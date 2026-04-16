from datetime import datetime
import logging
import os
import uuid
import pexpect
import six
import socket
import threading
import time

from session import Session
from vtestlogs import VLogging
from util import compare_version
import operator as op


class Confd(Session):
    '''
    Command-line (expect) Confd session to Viptela machine
    '''

    def __init__(self, machine, session=None, logger=None, **kwargs):
        self.logger = logger or VLogging(machine.name + '/confd').get_logger()
        self.machine = machine
        brought_session = False
        if session:
            brought_session = True
            self.session = session
        timeout = kwargs.get('timeout')  # connect timeout
        # timeout for enter and end config
        self.config_timeout = kwargs.get('config_timeout') or 1
        self.logger.debug(f'Confd({self.machine}) timeout={timeout}')
        super(Confd, self).__init__(machine.mgmt_ip, machine=machine,
                                    logger=self.logger, **kwargs)
        if not brought_session:
            self.set_screen_length()

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.machine.name)

    def configure(self, commands, attempts=5, timeout=20):
        '''
        Configure a single command or list of commands in bulk,
        using enter_config() and end_config().

        When talking to a cedge via a KVM console sent lines may be
        chopped in half causing syntax error.
        '''
        if not isinstance(commands, list):
            commands = [commands]
        self.enter_config()
        for command in commands:
            retries = 0
            success = False
            self.logger.debug(f'configure "{command}" on {self.machine.name}')
            while not success and retries < attempts:
                self.send(command)
                expected = [
                    'syntax error:.*(.*conf.*)#',
                    '(.*conf.*)#',
                    pexpect.TIMEOUT,
                ]
                index = self.prompt(expected, timeout=timeout)
                self.logger.debug(f'index {index}' f' self.before "{self.before}"' f' self.after "{self.after}"')
                if index == 1:  # normal prompt
                    success = True
                elif index == 0:  # syntax error:
                    self.logger.debug(f'Syntax error:  command {command}' f'retry {retries}')
                elif index == 2:  # timeout:
                    self.logger.debug(f'timeout:  command {command}' f'retry {retries}')
                time.sleep(1)  # sleep before a retry
                retries += 1
            if not success:
                self.logger.info(f'Failed to configure command {command}' f' on {self.machine.name}')
                return False
        return self.end_config()

    def set_screen_length(self):
        if isinstance(self.session, pexpect.spawn):
            massive = 10000
            self.session.maxread = massive
            self.send('screen-length %d' % massive)
            self.prompt()
            self.send('paginate false')
            self.prompt()

    def unhide_viptela(self):
        if compare_version(self.machine.version_check(), 20.4, op.lt):
            # Not even sure if this is needed anymore
            self.send('unhide viptela_internal')
            self.prompt(['.*password:', '.*Password:'])
            self.send('5mok!ngk!ll$')
            self.prompt()
        self._touch_testbed()

    def load_credentials(self):
        '''
        Override session.py because we for sure have a machine, not
        just an ip
        '''
        service = self.machine.get_service('confd')
        return service['username'], service['password']

    def get_password(self):
        passw = self.machine.config.get('password', 'admin')
        print(f'Confd::[{self.machine.name}] returning password {passw}')
        return passw

    def session_reducer(self, timeout=120):
        pexpect_args = {
            "encoding": "utf-8",
        }
        if six.PY3:
            pexpect_args["codec_errors"] = "ignore"
        child1 = pexpect.spawn(self.get_ssh_command(), timeout=timeout, **pexpect_args)
        child1.logfile = self.logger
        prompts = [
            '.*password:',
            'Password:',
            '.*SID of session to terminate.*:',
            'Select device personality:',
            self.default_prompt[0],
        ]
        done = False
        while not done:
            try:
                index = child1.expect(prompts)
                if index <= 1:
                    child1.sendline(self.get_password())
                elif index == 2:
                    assert index != 2, 'TODO: Out of sessions.'
                elif index == 3:
                    self.logger.info(
                        'Selecting device personality %d for %s' % (
                            self.machine.personality_num, self))
                    child1.sendline(str(self.machine.personality_num))
                    time.sleep(2)
                    done = True
                elif index > 3:
                    done = True
            except pexpect.EOF:
                return False
        return True

    def set_machine_personality(self, timeout=120):
        child1 = pexpect.spawn(self.get_ssh_command(), timeout=timeout, encoding='utf-8', codec_errors='ignore')
        child1.logfile = self.logger
        try:
            index = child1.expect([
                '.*password:', 'Password:']+self.default_prompt)
            if index <= 1:
                child1.sendline(self.get_password())
                index = child1.expect(['Select device personality:', '.*#'])
                if index != 0:
                    child1.close()
                    # May have already been set. TODO query it
                    return False
                self.logger.info('Selecting device personality %d for %s' % (
                                 self.machine.personality_num, self))
                child1.sendline(str(self.machine.personality_num))
                time.sleep(2)
                child1.close()
                return True
        except pexpect.EOF:
            return False
        return True

    def set_password(self, password=None, user='admin'):
        '''
        1. Unlock the account 'user'
        2. Set the password for 'user' via CLI
        3. Update config.yaml
        '''
        self.unhide_viptela()
        if compare_version(self.machine.version_check(), 20.9, op.eq) or compare_version(
            self.machine.version_check(), 20.11, op.gt
        ):
            self.send(f'request aaa unlock-user {user} reason faillock')
        else:
            self.send(f'request aaa unlock-user {user}')
        self.prompt()
        password = password or self.machine.config.get('password', 'admin')
        command = f'system aaa user {user} password {password}'
        if self.configure(command):
            self.machine.update_config_password(password, 'confd')
            return True
        msg = f'Failed to set password, see {self.machine.name}/confd.log'
        self.logger.info(msg)

    def query_certificate_serial(self):
        # Chassis number: c79d24da-630d-4a6e-96a5-b45812609f89
        # serial number: 12345709
        self.send('show certificate serial')
        self.prompt()
        serial = ''
        for line in self.after.splitlines():
            if 'serial number:' in line:
                items = line.split('serial number:')
                if len(items) < 2:
                    return ''
                serial = items[1].strip()
                break
        return serial

    def issue_commands(self, commands):
        for command in commands:
            self.send(command)
            index = self.prompt(
                [
                    '.*commit them?',
                    'control connection to the vManage',
                ]
                + self.default_prompt
            )
            if index == 0:
                self.send('yes')
                index = self.prompt(
                    [
                        'control connection to the vManage',
                    ]
                    + self.default_prompt
                )
                if index == 0:
                    self.send('no')
                    self.prompt()
            elif index == 1:
                logger = self.logger.get_runner_log()
                logger.info(f'{self.machine} Device is controlled'
                            ' by vManage, settings aborted.')
                self.send('no')
                self.prompt()

    def set_hostname(self):
        return self.configure(f'system host-name {self.machine.name}')

    def _touch_testbed(self):
        def send_and_relogin_if_required(cmd):
            self.send(cmd)
            index = self.prompt([pexpect.EOF] + self.default_prompt, timeout=120)
            if index == 0:
                self._new_session()

        tools_cmd = 'tools internal '
        if compare_version(self.machine.version_check(), 20.4, op.ge):
            tools_cmd = 'tools support '
        send_and_relogin_if_required(tools_cmd + 'touch_testbed')
        if 'syntax error' not in self.after:
            return
        # tools support didn't work so try tools internal or
        # or vice versa
        if tools_cmd == 'tools support':
            tools_cmd = 'tools internal '
        else:
            tools_cmd = 'tools support '
        send_and_relogin_if_required(tools_cmd + 'touch_testbed')

    def touch_testbed(self):
        self.unhide_viptela()
        # Create or remove /usr/share/viptela/test_root for allowing
        # any root cert for sw vedges.
        tools_cmd = 'tools internal '
        self.send(tools_cmd + 'touch_test_root')
        self.prompt()
        if 'File is touched' in self.after:
            return True
        self.last_error = self.after
        return False
        # TODO: Needs reboot?

    def set_testbed(self, testbed_host_ip='10.0.1.1'):
        command = f'vpn 0 host viptela.testbed ip {testbed_host_ip}'
        return self.configure(command)

    def set_site_id(self, site):
        # TODO: verify setting
        return self.configure(f'system site-id {site}')

    def set_vbond(self, host=None, port='12346'):
        '''
        DEPRECATED
        Use Netconf (see set_vbond in machine.py or its derivative)
        '''
        if ':' in host:
            host, port = host.split(':')
        config_port = f' port {port}' if port else ''
        if port == '12346':
            config_port = ''  # don't specify if it's default
        return self.configure(f'system vbond {host}{config_port}')

    def reset(self):
        self.send('request software reset')
        self.prompt([
            'Are you sure you want to reset to factory defaults? [yes,NO]'])
        self.send('yes')
        self.prompt()
        self.send('')
        self.send('exit')

    def show_software(self):
        '''
vm12# show software

VERSION       ACTIVE  DEFAULT  PREVIOUS  CONFIRMED  TIMESTAMP
-------------------------------------------------------------------------------
17.2.999-180  true    true     -         -          2019-06-17T23:29:44-00:00
19.2.999-198  false   false    false     -          -
        '''
        pass  # TODO

    def software_activate(self, version):
        '''
vm12# request software activate 19.2.999-198
This will reboot the node with the activated version.
Are you sure you want to proceed? [yes,NO]
        '''
        self.send('request software activate %s' % version)
        index = self.prompt(self.default_prompt + ['Are you sure you want to proceed?'])
        assert index == 1, 'Invalid response: %s' % (self.before + self.after)
        self.send('yes')
        return True

    def upload_serial_file(self, path, controller_list_upload=False):
        '''
        Upload serial list
        Note: controller-upload is available only on vbond and vmanage and not vsmart

        We will retry in speciffic cases (e.g. "already running by" error)
        and fail if it is just command error
        '''
        MAX_ATTEMPTS = 5
        PAUSE_BETWEEN_ATTEMPTS = 15

        target = 'controller-upload' if controller_list_upload else 'vedge-upload'
        attempts = MAX_ATTEMPTS
        output = ""
        try:
            while attempts > 0:
                self.send('request %s serial-file %s' % (target, path))
                self.prompt()
                output = self.before + self.after
                if "already running by" in output.lower():
                    attempts -= 1
                    if attempts:
                        self.logger.warning(
                            '%s: serial file upload unsuccessful, will wait %s seconds and retry (%s of %s)...'
                            % (self.machine.name, str(PAUSE_BETWEEN_ATTEMPTS), str(attempts), str(MAX_ATTEMPTS - 1))
                        )
                        time.sleep(PAUSE_BETWEEN_ATTEMPTS)
                        continue
                    self.logger.error(
                        '%s: serial file upload failed after %s attempts, last output: %s'
                        % (self.machine.name, str(MAX_ATTEMPTS), output)
                    )
                    return [False, output]
                if "error" in output.lower() or "failed" in output.lower():
                    self.logger.error('%s: serial file upload command failed: %s' % (self.machine.name, output))
                    return [False, output]
                self.logger.info('%s: serial file uploaded successfully' % (self.machine.name))
                return [True, output]
        except Exception as e:
            self.logger.error(
                '%s: serial file upload command failed: %s (%s %s)' % (self.machine.name, e, self.before, self.after)
            )
            return [False, str(self.before) + str(self.after)]

    def copy_internal_file(self, filepath):
        '''
        Make filepath accessible from tmp_filepath
        '''
        tmp_filepath = "/home/admin/" + str(uuid.uuid4()) + ".json"
        self.send('tools internal ip_netns options "exec default cp %s %s"' % (filepath, tmp_filepath))
        self.prompt()
        output = self.before + self.after
        if "No such file or directory" in output:
            return ""
        self.send('tools internal ip_netns options "exec default chmod a+r %s"' % tmp_filepath)
        return tmp_filepath

    def del_file(self, tmp_filepath):
        '''
        Del file from tmp_filepath
        '''
        self.send('tools internal ip_netns options "exec default rm %s"' % tmp_filepath)

    def show_version(self, timeout=10):
        self.send('show version')
        self.prompt(timeout=timeout)
        version = ''
        for line in self.after.split('\n'):
            if line.strip()[0].isdigit():
                version = line.strip().split(' ')[0]
        if not version:
            # No idea. Just return the next line in the output
            # after the command
            return self.after.split('\n')[1]
        return version

    def set_time(self, dt=None):
        dt = dt or datetime.utcnow()
        self.send('clock set time ' + dt.strftime('%H:%M:%S.%f')[:-3] +
                  ' date ' + dt.strftime('%Y-%m-%d'))
        self.prompt()

    def set_current_time(self):
        return self.set_time(datetime.utcnow())

    def install_root_cert(self, cert_file):
        if not cert_file.startswith('/'):
            cert_file = f'/home/admin/{cert_file}'
        self.send(f'{self.machine.sdwan_request} root-cert-chain install {cert_file}')
        # Successfully installed the root certificate chain
        # OR
        # Failed to install the root certificate chain !!
        self.prompt()

    def setup_netconf_interface(self, ifname, ipaddr, mask_bits):
        if not isinstance(ifname, list):
            ifname = [ifname]
        interface_cmd = 'vpn 0 interface {iface} ip address {ip}/{pref}'
        for name in ifname:
            cmd = interface_cmd.format(iface=name, ip=ipaddr, pref=mask_bits)
            self.configure(cmd)

    def generate_csr(self):
        self.logger.info("Generate csr on vm: %s" % self.machine)
        org_name = self.machine.get_org_name()
        child = pexpect.spawn(self.get_ssh_command(), encoding='utf-8', codec_errors='ignore')
        try:
            child.expect('.*#')
            child.sendline('request csr upload /home/admin/csr')
            child.expect(
                "Enter [O|o](rganization-unit)|(rganization) name            :")
            child.sendline(org_name)
            child.expect(
                "(Re-enter)|(ReEnter) [O|o](rganization-unit)|(rganization) name          :")
            child.sendline(org_name)
            child.expect(["CSR upload successful", pexpect.EOF])
        finally:
            child.close()

    def install_signed_certificate(self, cert_file):
        if os.path.basename(cert_file) == cert_file:
            cert_file = os.path.join('home', 'admin', cert_file)
        self.send('%s certificate install %s' % (self.machine.sdwan_request,
                                                 cert_file))
        self.prompt()

    def unshut_interface(self, ifname, vpn):
        commands = [
            f'vpn {vpn}',
            f'interface {ifname}',
            'no shutdown',
        ]
        return self.configure(commands)

    def get_running_config(self):
        command = 'show running-config'
        self.send(command)
        self.prompt()
        contents = self.before + self.after
        lines = contents.splitlines()
        if lines[0].strip().startswith(command):
            # remove command itself from the beginning
            del lines[0]
        if not lines[-1].startswith('!'):
            # remove junk at the end
            del lines[-1]
        contents = '\n'.join(lines)
        return contents

    def set_system_ip(self, ip=''):
        ip = ip or self.machine.get_system_ip_no_mask()
        self.configure(f'system system-ip {ip}')
        return ip

    def config_tunnel(self, ifname, vpn):
        commands = [
            f'vpn {vpn}',
            f'interface {ifname}',
            'tunnel-interface',
        ]
        return self.configure(commands)

    def shut_interface(self, ifname, vpn):
        commands = [
            f'vpn {vpn}',
            f'interface {ifname}',
            'shutdown',
        ]
        return self.configure(commands)

    def software_install(self, image_name, threaded=False):
        '''
        :image_name: is a filepath local to the machine.
        Returns: The version string that is installed.
Allowing ENG cert in TESTBED
Signature verification Suceeded.
Successfully installed version: 19.2.999-198
        '''
        self.send('request software install %s' % image_name)
        index = self.prompt(
            self.default_prompt + ['Successfully installed version:'],
            timeout=600
        )
        if index == 0:
            self.logger.info(self.before + self.after)  # debug?
            return ''
        version = ''
        for line in self.after.splitlines():
            if line.startswith('Successfully installed version:'):
                version = line.split(
                    'Successfully installed version:')[1].strip()
        if threaded:
            threading.current_thread().viptela = {
                'machine': self.machine.name,
                'versions': {
                    'platform': '',
                    'vmanage': version,
                }
            }
        return version

    def load_config(self):
        '''
        Function must be overrided for cEdges

        1. Copy config file to the machine.
        2. Load the config into the running-config configuration.
        '''
        self.configure(f'load override /home/admin/{self.machine.name}_config')

    def cmd_show_omp_peers(self):
        self.send('show omp peers')
        self.prompt()
        return self.after

    def get_omp_peers(self):
        #                         DOMAIN    OVERLAY   SITE
        # PEER             TYPE    ID        ID        ID        STATE    UPTIME           R/I/S
        # -----------------------------------------------------------------------------------------
        # 172.16.255.11    vedge   1         1         100       up       2:19:04:20       20/0/49
        # 172.16.255.14    vedge   1         1         400       up       2:19:04:26       2/0/60
        # 172.16.255.15    vedge   1         1         500       up       2:19:04:31       21/0/43
        output = self.cmd_show_omp_peers()
        data = {}
        headers = []
        keys = ['peer', 'type', 'domain-id', 'overlay-id',
                'site-id', 'state', 'uptime', 'r/i/s']
        data = []
        num_keys = 0
        for line in output.splitlines():
            if line.startswith('----------'):
                num_keys = max([len(l.split()) for l in headers])
                self.logger.debug('number of keys: {}'.format(num_keys))
                assert num_keys == len(keys), 'Parse error in show omp peers.'
                continue
            if not num_keys:
                headers.insert(0, line)
                continue
            items = line.split()
            if len(items) < num_keys:
                break
            element = {}
            for index, key in enumerate(keys):
                element[key] = items[index]
            data.append(element)
        return data

    @property
    def config_command(self):
        return 'config'

    def enter_config(self, attempts=5, timeout=None):
        '''
        Upon entering configutaion mode there may be pending
        configuration changes that need to be cleared.
        Discard or commit based on the system prompt.
        Return True if this was successful
        '''
        if timeout is None:
            timeout = self.config_timeout
        self.logger.debug('ENTER CONFIG')

        retries = 0
        success = False
        self.send(self.config_command)
        while not success and retries < attempts:
            retries += 1
            expected = [
                'There are uncommitted changes. Discard changes.',
                'Uncommitted changes found, commit them. .yes/no/CANCEL.',
                '(.*conf.*)#',
                pexpect.TIMEOUT,
            ]
            index = self.prompt(expected, timeout=timeout)
            self.logger.debug(f'index {index}' f' self.before "{self.before}"' f' self.after "{self.after}"')
            if index == 3:  # timeout
                self.send('\r')
                time.sleep(1)  # sleep before a retry
                continue
            elif index == 0:  # Discard changes.
                self.send('yes')
                self.prompt()
            elif index == 1:  # there are uncommited changes
                self.send('no')
                self.prompt()
            success = True
        self.send('top')
        self.prompt()
        return success

    def respond_to_commit_them(self, timeout=1):
        '''
        This dialog may encountered when entering and exiting
        config mode.  Return True unles commit was aborted.
        '''
        self.logger.debug('RESPOND TO COMMIT')
        expected = [
            'Uncommitted changes found, commit them. .yes/no/CANCEL.',
            'Commit complete',
            'No modifications to commit',
            'Aborted: by user',
            'Aborted',
            'Proceed. .yes,no. ',
            self.default_prompt[0],
        ]
        self.send('yes')
        time.sleep(3)  # gen config can take a second
        # index = self.prompt(expected, timeout=timeout)
        index = self.prompt(expected, timeout=90)
        self.logger.debug(f'index {index}' f' self.before "{self.before}"' f' self.after "{self.after}"')
        assert index != 4, self.after  # Aborted (generic)
        return True

    def end_config(self, attempts=5, timeout=20):
        '''
        When exiting configutaion mode the pending
        configuration changes need to be committed.
        Return True upon success, assert on Abort,
        otherwise return False.
        :attempts: are to give it more tries in case of a timing
        conflict, as vmanage or another process may be making an
        unrelated update.
        '''
        retries = 0
        success = False
        self.logger.debug('END CONFIG')
        self.send('end')
        time.sleep(3)  # gen config can take a second
        while not success and retries < attempts:
            expected = [
                'Uncommitted changes found, commit them. .yes/no/CANCEL.',
                '(.*conf.*)#',
                'Commit complete',
                'No modifications to commit',
                self.default_prompt[0],
                pexpect.TIMEOUT,
            ]
            index = self.prompt(expected, timeout=timeout)
            self.logger.debug(f'index {index}' f' self.before "{self.before}"' f' self.after "{self.after}"')
            if index >= 2 and index <= 4:  # normal prompt
                success = True
                break
            elif index == 0:  # there are uncommited changes
                self.respond_to_commit_them(timeout=timeout)
                success = True
                break
            elif index == 1:  # we got config prompt
                continue
            time.sleep(1)  # sleep before a retry
            retries += 1
        self.send('\r')
        self.prompt()
        return success

    def request_admin_tech(self, timeout=120):
        # cedge needs \r\n at the end?
        self.send(f'{self.machine.sdwan_request} admin-tech')
        self.prompt(timeout=timeout)
        for line in self.after.splitlines():
            if 'Created admin-tech file' in line:
                break
        if 'Created admin-tech file' not in line:
            self.logger.info('%s admin-tech not created?' % self.machine.name)
            return None
        full_name = line.split(' ')[-1].replace("'", '')
        return full_name

    def add_usergroup(self, group='vtest-add-group', tasks=[]):
        '''
        system aaa
         usergroup {group}
          task system read write
          ...

        where tasks =
        [{'read': True, 'write': True, 'enabled': True, 'feature': 'system'},
         {'read': True, 'write': True, 'enabled': True, 'feature': 'interface'},
         {'read': True, 'write': True, 'enabled': True, 'feature': 'policy'},
         {'read': True, 'write': True, 'enabled': True, 'feature': 'routing'},
         {'read': True, 'write': True, 'enabled': True, 'feature': 'security'}]
        '''
        commands = [
            'system aaa',
            f'usergroup {group}',
        ]
        for task in tasks:
            if task['enabled']:
                assert task['read'] and task['write'], (
                    "'system aaa task system oper-exec" " default-action' is not configured"
                )
                command = f'task {task["feature"] }'
                command = command + ' read' if task['read'] else command
                command = command + ' write' if task['write'] else command
                commands.append(command)
        return self.configure(commands)

    def delete_usergroup(self, group='vtest-add-group'):
        '''delete usergroup {group}'''
        commands = [
            'system aaa',
            f'no usergroup {group}',
        ]
        return self.configure(commands)

    def add_user(
        self, group='netadmin', description='"vtest add user"', username='vtest-add-user', password='password'
    ):
        '''Add username with group, description and password using CLI'''
        commands = [
            'system aaa',
            f'user {username}',
            f'password {password}',
            f'group {group}',
            f'description {description}',
        ]
        return self.configure(commands)

    def delete_user(self, username):
        '''delete user {username}'''
        commands = [
            'system aaa',
            f'no user {username}',
        ]
        return self.configure(commands)

    def ping(self, ip, vpn=0, vrf=None, repeat=5, timeout=2):
        """
        ping count 1 vpn 512 10.20.30.40
        Check for packets transmitted or error in output and return that line.
        """
        if vpn is None:
            vpn = 0
        self.send(f"ping count {repeat} vpn {vpn} wait {timeout} {ip}")
        self.prompt()
        expected_text = ["packets transmitted", "ping:", "syntax error"]
        for line in self.after.splitlines():
            if any(text in line for text in expected_text):
                break
        pass_text = f"{repeat} packets transmitted, {repeat} received, 0% packet loss"
        return (pass_text in line, f"ping vpn {vpn} {ip} output: {line}")

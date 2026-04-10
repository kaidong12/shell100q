from vtestpaths import Paths
from past.builtins import unicode
from distutils.version import LooseVersion
from pathlib import Path
from pprint import pformat
from selinux import platform_mapping
from selinux import reg_eval
import signal
from queue import Empty
from collections import Counter
import sys
import re
import os
import argparse
import time
import logging
import pexpect
import vtest_logging
import common_runner
from debug_callback import DebugCallback
from executioner import Executioner
from enum import IntEnum
import socket
import code
import pwd
import smtplib
import shutil
import inspect
import random
import queue
import multiprocessing
import difflib
import yaml
import email.mime.text
import email.mime.multipart
import traceback
import misc
import datetime
import json
import io
import zipfile
import distro
import string
import glob
from threading import Thread
from preference import pref, reload_preference
from data import Tests
from configs import Configbuilder
from sessions.abstract import AbstractSession
from sessions import IOSXENetconf
from sessions import ViptelaSession
from sessions import CONFDSession
from sessions import IOSXESession
from sessions import SpirentSession
from sessions import IxiaSession
from sessions import ISESession
from sessions import ADSession
from sessions import WWANSession
from sessions import CiscoSession
from sessions import VMANAGESession
from sessions import VMANAGESession_system
from sessions import CombinedShowSession
from sessions import VmanageGUISession
from sessions import ProtractorSession
from sessions import LandslideSession
from sessions import JmeterSession
from sessions import XMLgenerator
from sessions import VmanageSSH
from sessions import VManageSession
from sessions import RobotSession
from sessions import CiscoSparkSession as Spark
from sessions import RoutingVmanageREST
from sessions import ForwardingVmanageREST
from sessions import ServicesVmanageREST
from sessions import PolicyVmanageREST
from sessions import MTPolicyVmanageREST
from sessions import MTForwardingVmanageREST
from sdwan_version import SdwanVersion
from hypervisor import HyperVisor
from testbed import (
    Testbed,
    TestbedException,
)
import sqldb
import sqldb_rest
import timeit
import vtest  # noqa
import config_utils
import update_tb
from suitemodules import SuiteModules
from machines import Machines
from vlock import vLock
from vtest_backup_logs import LogBackup
from vtestlogs import VLogging, TcSrcCodeLogging, LibsLoggerController
from sessions import UploadTest
from os.path import expanduser
import crft_export_lib
import ctc
from reports import TestStats, TCResult
from reports.xml import SummaryXML
import tarfile
import requests
from codecoverage import VmanageCodeCoverage
import cert_validation
from logclean import CleanLogsHandler
from util import normalize_builds, get_location_version, compare_version
from okta_auth import OktaAuth
from vtest_constants import DEFAULT_BRANCH
import operator as op
from utils.app_args import diff_namespaces
from utils.bugbuddy_utils import BugBuddyUtil
from utils.vmonitor_utils import launch_vmonitor, send_signal_to_vmonitor
from utils.misc_utils import list_all_threads_and_processes, debug_threads_init, unpack_tar_gz
from utils.tests_utils import (
    get_testbed_version,
    verify_possible_parallel_subtests_collisions,
    verify_possible_parallel_block_subtests_collisions,
    calculate_parallel_subtests,
    diagnose_vmanage,
)
from ucs_host import UCSHost
from global_param import GlobalParam
from profiling import create_profiler
import platform

if sys.version_info <= (3, 2):
    import subprocess32 as subprocess
else:
    import subprocess
from importlib import import_module

if 'pagent' in pref:
    from sessions import PagentSession

try:
    import typing
    import vtyping
except ImportError:
    pass

devnull = open(os.devnull, 'wb')

from vtest_constants import (
    MACHINE_SESSION_PEXPECT_TIMEOUT,
    TEST_INFO_INDEX_OF_TC_RESULT,
    TEST_INFO_INDEX_OF_BUG_ID,
)
from smart_debug import SmartDebug
from org_name_reservation import unreserve_org_name
from tools import set_log_root, notify_user_by_webex

class RunnerExitCode(IntEnum):
    SUCCESS = 0
    GENERIC_FAILURE = 1


class SkippedTCException(Exception):
    """Used for reporting TCs that are either selected to be skipped by user or by TC author"""


class BlockedTCException(Exception):
    """Used for reporting TCs that are blocked either by previous failure or error"""


class TimeoutTCException(Exception):
    """Used for reporting TCs that are taking too long time"""

    # Unit is obligatory after integer
    pattern = r'(\d+)([dhms])'

    @staticmethod
    def tc_timeout_arg_type(val_str):
        """For argparese parameter validation"""
        match = re.match(TimeoutTCException.pattern, val_str)
        if match:
            return val_str

        raise argparse.ArgumentTypeError(
            "'%s' is not a correct TC timeout to match with r'%s' (some examples are: 20s or 30m or 3h or 2d )"
            % (val_str, TimeoutTCException.pattern)
        )

    @staticmethod
    def parse_str_val(val_str):
        # keys expected by datetime.timedelta()
        template = {'days': 0, 'hours': 0, 'minutes': 0, 'seconds': 0}
        match = re.match(TimeoutTCException.pattern, val_str)
        if match:
            val = int(match.group(1))  # First group: the integer
            unit = match.group(2)  # Second group: the unit (s, m, h, or d)
            for k in template.keys():
                # look for s h m s at the beginning of the key
                if k[0] == unit:
                    template[k] = val
                    break  # expect only single unit

        return (True if match else False, int(datetime.timedelta(**template).total_seconds()))

    # used as a tag in TTF file, i.e.:
    # vexpress - test_load_express_config     = ['setup', 'tc_timeout=4h']
    look_for_tag = 'tc_timeout'
    tout_default_val = '2d'
    tout_val_sec = 172800  # 2 days

    @classmethod
    def set_tout_val(cls, tout_val_str):
        ret, val_sec = cls.parse_str_val(tout_val_str)
        if ret:
            cls.tout_val_sec = val_sec
        return ret

    @classmethod
    def get_tout_val(cls):
        return cls.tout_val_sec

    @classmethod
    def get_tout_val_human(cls, tout_val_sec=None):
        if tout_val_sec is None:
            ret_str = str(datetime.timedelta(seconds=cls.tout_val_sec))
        else:
            ret_str = str(datetime.timedelta(seconds=tout_val_sec))
        # expected format by split: 0:00:00   h m s
        # or for longer than day durations
        # expected format by split: 1 day, 0:00:22   h m s
        return "{}h:{}m:{}s".format(*ret_str.split(':'))


# should be same value as vmonitor.const STUCK_LIMIT_MARK_TIME_SEC
STUCK_LIMIT_MARK_TIME_SEC = 3630

# Low-level values representing a test case's result,
# returned from execute() and process_subtests():
# the test case passed
RETVAL_SUCCESS = 0
# the test case failed
RETVAL_FAILURE = 1
# the test case raised an exception
RETVAL_ERRORED = 2
# the test case function itself
# (which should return a list of subtests to execute)
# raised an exception (before actual subtest execution),
# or a KeyboardInterrupt happened
RETVAL_OTHER = -1
# spirent library call thrown exception
RETVAL_ERROR_SPIRENT_RUNTIME = -2
# initial value to be overriden by process_subtests()
RETVAL_ERROR_DEFAULT = -3
# informs that core files were found after TC run , used to propgate failure even if test got pass
RETVAL_ERROR_ERROR_CORE_FILES_FOUND = -4

class Color(object):
    RED = '\033[1;31m'
    GREEN = '\033[1;32m'
    YELLOW = '\033[1;33m'
    RESET = '\033[0m'

    BG_RED = u'\u001b[41m'
    BG_RESET = u'\u001b[0m'


runner_keyboard_interrupted = False


def handle_sigint(signum, frame):
    global runner_keyboard_interrupted
    runner_keyboard_interrupted = True
    raise KeyboardInterrupt


class Runner(object):
    """
    Main class for testbed runner
    """

    global WIDTH, MAX_NUM_OF_PROCS
    global SPARK_BOT_TOKEN
    WIDTH = 50
    #CHANGE: Just picked an arbitrary number, actually figure out the best value
    MAX_NUM_OF_PROCS = 25
    SPARK_BOT_TOKEN='NTY3ZTA5M2ItNzBlOC00NWI2LWE2ZjItNDllOGMzMWFkZmU5OWNmZDlmZjgtY2E1'

    def main(self) -> int:
        """Main function of the runner"""
        #Get the start timestamp for the run
        self.start = time.time()
        debug_threads_init()
        signal.signal(signal.SIGINT, handle_sigint)
        #Store the entire list of arguments in a string
        self.executor = sys.argv[0]
        self.args_string = ' '.join(sys.argv[1:])
        self.tests_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            levels = pref['levels']
        except KeyError:
            levels = 'No levels currently defined'

        self.bugbuddy_util = BugBuddyUtil()

        #Get and parse all the arguments from the command line
        self.parser = parser = argparse.ArgumentParser()
        parser.add_argument('suite', help='The test suite/file to run, or the path to the file', action='store')

        parser.add_argument('-cbd', '--callback_debug', help='Enable Callback Debuggability', action='store_true')
        parser.add_argument('-loc', '--local', help='Run the tests locally with a local patch', action='store_true')
        parser.add_argument(
            '-fp', '--file_path', help='The path of the file you want to use as the patch', action='store'
        )
        parser.add_argument(
            '-kcc',
            '--keep-checksum-cache',
            action='store_true',
            help="Image checksums cache gets cleared unless you specify -kcc",
        )
        parser.add_argument(
            '-r',
            '--remote',
            help='Run the tests on a remote server. Takes the remote machine, and the images(could be a patch.zip file or a dir containing all the complete images) to use as arguments. Ex: user@ip_address ~/local/images',
            nargs=2,
        )
        parser.add_argument(
            'yaml_file',
            nargs='?',
            help='This can specify a protocol yaml but is often ignored. Correct argument to use is --protocol-yaml',
            action='store',
        )
        tags_parser = parser.add_mutually_exclusive_group(required=False)
        tags_parser.add_argument(
            '-t',
            '--tags',
            action='append',
            default=[],
            help='Specify a tag. Use repeatedly for multiple tags. Ex: -t "configure" -t "check"',
        )
        tags_parser.add_argument(
            '-tr',
            '--tags_range',
            action='append',
            nargs=2,
            help='Provide a start and an end test case name. This will run all the tests from the start test case to the end test case, with the start and end cases included',
        )
        parser.add_argument(
            '-con',
            '--console_connection',
            action='append',
            default=[],
            help='Specify PM to add console session to confd. Use pmXX. Ex: -con pm3 -con pm4',
        )
        parser.add_argument(
            '-doc', '--documentation', action='store_true', help='Help on runner suite. Usage: runner <suitename> -doc'
        )
        parser.add_argument(
            '-et',
            '--exclude_tags',
            action='append',
            default=[],
            help='E.T. (something out of this world). Use this option to exclude certains tests from the run. Ex: -et test_config_vdaemon -et test_flap_interfaces',
        )
        parser.add_argument(
            '-l',
            '--level',
            action='store',
            help='Which level tests cases to run. These levels are defined in the preference.yaml: %s' % levels,
        )
        parser.add_argument('-v', '--verbose', help='See more output', action='store_true')
        parser.add_argument('-no_lock', '--no_lock', action='store_true', help='')
        parser.add_argument('-terraform_state', '--terraform_state', action='store', help='')
        parser.add_argument(
            '-n',
            '--new_testbed',
            action='store',
            help='Create a new testbed and then run tests scripts on it (takes the testbed location as an argument)',
        )
        parser.add_argument(
            '-o',
            '--overwrite',
            action='store_true',
            help='Use in conjunction with --new_testbed(-n). If a testbed with the name of the new_testbed already exists it is overwritten',
        )
        parser.add_argument(
            '-a',
            '--additional',
            action='store',
            help='Use in conjunction with --new_testbed(-n). Use to pass in the optional aditional argument for the new testbed (build number, STABLE|LATEST and other folder name lables).',
        )
        parser.add_argument(
            '-ca',
            '--cedge_build',
            action='store',
            help='Use in conjunction with --new_testbed(-n). Use to pass in cedge build optional argument for the new testbed (STABLE|LATEST|PREVIOUS_STABLE and other folder name labels).',
        )
        parser.add_argument(
            '-cb',
            '--cedge_branch',
            action='store',
            help='Use in conjunction with --new_testbed(-n). Use to pass in cedge branch optional argument for the new testbed (polaris_dev and throttles).',
        )
        parser.add_argument(
            '-va',
            '--vedge_build',
            action='store',
            help='Use in conjunction with --new_testbed(-n). Use to pass in vedge build optional argument for the new testbed (STABLE|LATEST|PREVIOUS_STABLE and other folder name labels).',
        )
        parser.add_argument(
            '-prot',
            '--protocol-yaml',
            action='store',
            help='Name of protocol yaml (expected to be in yamls/protocols)',
        )
        parser.add_argument('-vtd', '--version_to_download', action='store', help='Version to download for ztp upgrade')
        parser.add_argument('-cvu', '--cedge_version_upgrade', action='store', help='Version to upgrade for cedge. Need to pass entire ftp link')
        parser.add_argument('-ccu', '--cedge_container_upgrade', action='store', help='Version to upgrade for mips vedge. Used in cEdgeUpgrade suite. Need to pass entire ftp link')
        parser.add_argument('-vvu', '--vmanage_version_upgrade', action='store', help='Version to upgrade for vmanage. Used in cEdgeUpgrade suite. Need to pass entire ftp link')
        parser.add_argument('-evu', '--vedge_version_upgrade', action='store', help='Version to upgrade for vedge and vsmart devices. Used in cEdgeUpgrade suite. Need to pass entire ftp link')
        parser.add_argument(
            '-avu',
            '--aon_eio_version_upgrade',
            action='store',
            help='Version to upgrade for aon and eio devices. Used in Highrise suite. Need to pass entire ftp link/ auto path',
        )
        parser.add_argument(
            '-smu',
            '--software_maintenance_upgrade',
            action='store',
            help='Version to maintenance upgrade. Need to pass entire ftp link',
        )
        parser.add_argument(
            '-non_dmz_ip', '--non_dmz_ip', action='store', help='Passes the non_dmz ubuntu ip address for ssh.'
        )
        parser.add_argument(
            '-ubuntu_client_dns_resolver_ip',
            '--ubuntu_client_dns_resolver_ip',
            action='store',
            help='the name-server IP address in /etc/resolv.conf of Ubuntu services.',
        )
        parser.add_argument(
            '-edge_name_server_ip', '--edge_name_server_ip', action='store', help='Passes the edge name server ip.'
        )
        parser.add_argument('-secret_access_aws', '--secret_access_aws', action='store', help='AWS secret password.')
        parser.add_argument('-cxp_loss', '--cxp_loss_percentage', action='store', help='CXP loss percentage for probe verification.')
        parser.add_argument('-cxp_latency', '--cxp_latency', action='store', help='CXP latency in milli seconds for probe verification.')
        parser.add_argument('-emu', '--vedge_mips_upgrade', action='store', help='Version to upgrade for mips vedge. Used in cEdgeUpgrade suite. Need to pass entire ftp link')
        parser.add_argument('-itd', '--image_to_download', action='store', help='Image to download for ST-MTT feature testing')
        parser.add_argument('-id', '--identifier', action='append', default=[], help='Specify stress test Id from vtest/addons/system_stress_events/eventFile.txt. Ex: -id "1"')
        parser.add_argument('-systopo', '--systopo', action='append', nargs='+', default=[], help='Specify topology for systbed. Ex: -systopo enableTLS max_controllers enableHubSpoke')
        parser.add_argument('-df', '--different_image_type', action='store', help='Specify a different image type from the default one (ex: dbg image rather than the regualr non-debug one)')
        parser.add_argument('-x', '--stopatfail', help='Stop execution at first failure', action='store_true')
        parser.add_argument(
            '-tcto',
            '--testcase_timeout',
            type=TimeoutTCException.tc_timeout_arg_type,
            help='Time after TC is set to TIMEOUT if runs longer than specified time. Time unit [s|m|h|d] is required, i.e. -tcto 240s,  -tcto 120m, -tcto 3h',
            action='store',
            default=TimeoutTCException.tout_default_val,
        )
        parser.add_argument('-i', '--interactive', help='Run tests interactively with pausing ability within tests', action='store_true')
        parser.add_argument('-d', '--debug', help='Turn on debug mode', action='store_true')
        parser.add_argument('-c', '--cleanup', help='Take down the testbed once tests are done', action='store_true')
        parser.add_argument('-p', '--patch', action='append', help='Specify the machine types on which to apply the patches, only works with remote submissions (-r/--remote)')
        parser.add_argument('-C', '--count', action='store', help='The number of times that you want to run the tests')
        parser.add_argument('-ra', '--randomize', action='store_true', help='randomize the order in which tests are run')
        parser.add_argument('-f', '--fresh', action='store_true', help='Start tests with an empty and fresh CDB')
        parser.add_argument('-b', '--branch', action='store', help='The branch whose image needs to be pulled (ex: 0.0/1.0)')
        parser.add_argument('-w', '--windows', action='store_true', help='Run selinum server on windows host')
        parser.add_argument('-pr', '--prompt', action='store_true', help='Interactive prompt for accessing vtest libraries')
        parser.add_argument('-u', '--upgrade', action='store', help='Upgrade the testbed image before running the tests', nargs='?', default='')
        parser.add_argument('-pn', '--print_netconf', action='store_true', help='Print netconf xml trees')
        parser.add_argument('-vmd', '--http_debug', action='store_true', help='Print vmanage request url')
        parser.add_argument('-nd', '--ncclient_debug', action='store_true', help='Enable ncclient debugs')
        parser.add_argument('-V', '--enable_valgrind', action='store_true', help='Enable default valgrind configurations')
        parser.add_argument('-y', '--yaml', action='store', help='The yaml file to use for creating the testbed')
        parser.add_argument('-gc', '--generate_configs', action='store_true', help='Generate the config files for suite setups')
        parser.add_argument('-lc', '--load_configs', action='store', help='Load the config files for suite setups', nargs='*', default=False)
        parser.add_argument('-sc', '--save_configs', action='store', nargs='*', help='save the config files for suite setups')
        parser.add_argument('-ech', '--enable_ciscohosted', action='store_true', help='Enable cisco cloud hosted')
        parser.add_argument('-ncl', '--disable_pm_console_logger', action='store_true', help='Disable console logger')
        parser.add_argument('-ntg', '--no_traffic_generation', action='store_true', help='Do not run tests with Spirent traffic generator')
        parser.add_argument('-iub', '--include_ubuntu', action='store_true', help='include ubuntu vm in topology')
        parser.add_argument('-rub', '--reboot_ubuntu', action='store_true', help='reboot ubuntu vm in topology')
        parser.add_argument('-dub', '--dynamic_ubuntu', action='store_true', help='reboot ubuntu vm in topology')
        parser.add_argument(
            '-ubi',
            '--ubuntu_image',
            action='store',
            help='Path to ubuntu qcow2 image',
            default=str(Path.home() / 'local_ubuntu_services' / 'ubuntu_services.qcow2'),
        )
        parser.add_argument(
            '-uc',
            '--ucs_cleanup',
            default=False,
            action='store_true',
            help='clean up the UCS before testbed bringup',
        )
        parser.add_argument('-iise', '--include_ise', action='store_true', help='include ise vm in topology')
        parser.add_argument('-rise', '--reboot_ise', action='store_true', help='reboot ise vm in topology')
        parser.add_argument('-iad', '--include_ad', action='store_true', help='include ad vm in topology')
        parser.add_argument('-rad', '--reboot_ad', action='store_true', help='reboot ad vm in topology')
        parser.add_argument(
            '-fwconfig',
            '--firewall_config',
            action='store',
            default='',
            help='firewall config input file for ruleset optimization',
        )
        parser.add_argument(
            '-non_dmz', '--non_dmz', action='store_true', help='to handle non dmz testbeds for security suites'
        )
        parser.add_argument(
            '-restapi', '--restapi_test', action='store_true', help='to handle rest api testing for suites'
        )
        parser.add_argument(
            '-cli_template',
            '--cli_template_test',
            action='store_true',
            help='to handle rest api cli template testing for suites',
        )
        parser.add_argument(
            '-tstl',
            '--trex_stateless_generator',
            action='store',
            nargs='?',
            type=str,
            const='',
            help='Use T-Rex in stateless mode',
        )
        parser.add_argument(
            '-tstf',
            '--trex_stateful_generator',
            action='store',
            nargs='?',
            type=str,
            const='',
            help='Use T-Rex in stateful mode',
        )
        parser.add_argument(
            '-rtg', '--reconnect_traffic_generator', action='store_true', help='Reconnect to existing Spirent Test'
        )
        parser.add_argument('-ne', '--no_email', action='store_true', help='Do not send emails')
        parser.add_argument('-rtc', '--random_tloc_color', action='store_true', help='Pick a random color for tlocs (default is lte)')
        parser.add_argument('-ktga', '--keep_traffic_generation_alive', action='store_true', help='Do not kill Spirent traffic generator session')
        parser.add_argument('-er', '--enable_short_rekey', action='store_true', help='Stop automatic change of the rekey timer to 60s')
        parser.add_argument('-rc', '--remove_core_files', action='store_true', help='Removes any core files under the old_dumps directory in /var/crash')
        parser.add_argument('-m', '--message', action='store', help='A message to specify the reason for this submission/run')
        parser.add_argument('-rrd', '--randomly_restart_daemons', action='store_true', help='Restart random daemons at random points in testing')
        parser.add_argument('-ivm', '--include_vmanage', action='store_true', default=True, help='Run tests with vmanage configured')
        parser.add_argument('-evm', '--exclude_vmanage', action='store_true', help='Exclude vmanage machine from topo')
        parser.add_argument('-pass', '--getpass', action='store_true', help='Get vmanage password')
        parser.add_argument('-user', '--getuser', action='store_true', help='Get vmanage username')
        parser.add_argument('-fg', '--force_generate', action='store_true', help='Force run apigen by removing .bak files')
        parser.add_argument('-vman', '--vmanage_ips', action='append', default=[], help='Specify a vmanage IP or IP range. Use repeatedly for multiple IPs. Ex: -vman 1.1.1.1 -vman 1.1.1.2 or -vman 1.1.1.1-3 for 1.1.1.1, 1.1.1.2, and 1.1.1.3')
        parser.add_argument('-ver', '--vmanage_version_compare', action='store', help='Specify a vmanage version to compare api changes. Ex: -ver 16.1')
        parser.add_argument('-ihdp', '--include_hdp', action='store_true', help='include hdp machine vm15 in topology')
        parser.add_argument('-tlocExt_gre', '--include_tlocExt_gre', action='store_true', help='include tlocExt_gre machine vm24 in topology')
        parser.add_argument('-ivs3', '--include_vs3', action='store_true', help='include vs3 machine vm14 in topology')
        parser.add_argument('-ivs4', '--include_vs4', action='store_true', help='include vs3 and vs4 machine vm14/vm17 in topology')
        parser.add_argument('-ivs20', '--include_vs20', action='store_true', help='include 20 vmsart machine vm14/vm17, vm20-vm35 in topology')
        parser.add_argument('-ivb23', '--include_sec_vb23', action='store_true', help='include secondary vbond machine vm23 in topology')
        parser.add_argument('-isvm', '--include_scaling_vmanage', action='store_true', help='include vman2 vm18 and vman3 vm19 in topology')
        parser.add_argument('-isvm6', '--include_scaling_vmanage6', action='store_true', help='include vman2 vm18, vman3 vm19, vman4 vm20, vman5 vm21, vman6 vm22 in topology')
        parser.add_argument('-ntr', '--no_transport_routing', action='store_true', help='Bring up OMP suite without OSPF transport routing')
        parser.add_argument('-tvpn', '--transport_vpn', action='store_true', help='Run OSPF/BGP test suite for Transport VPN')
        parser.add_argument('-tls', '--tls', action='store_true', help='Use TLS for control connection')
        parser.add_argument('-nrcc', '--nrcc', action='store_true', default=False, help='Disable route consistency check')
        parser.add_argument('-trans_ipv6', '--trans_ipv6', action='store_true', help='Use Ipv6 as transport address type')
        parser.add_argument('-ipv6_ra', '--ipv6_ra', action='store_true', help='Use Ipv6 as transport address type with SLAAC')
        parser.add_argument('-serv_ipv6', '--serv_ipv6', action='store_true', help='Use Ipv6 as service address type.')
        parser.add_argument('-ipv6', '--ipv6', action='store_true', help='Use Ipv6 as service and transport address type.')
        parser.add_argument('-vs_pol_bld', '--vsmart_policy_builder', action='store_true', help='Use vManage to configure policies on vSmarts')
        parser.add_argument('-innat', '--enable_internal_nat', action='store_true', help='Configure Internal NAT')
        parser.add_argument('-cflowd_udp', '--enable_cflowd_transport_udp', action='store_true', help='Configure CFLOWD Transport UDP')
        parser.add_argument('-dpi', '--enable_dpi', action='store_true', help='Configure DPI on vEdges')
        parser.add_argument('-svg', '--show_vmanage_gui', action='store_true', help='Show the vmanage gui in the browser when running the vmanage_gui suite')
        parser.add_argument('-R', '--run_remotely', action='store', help=argparse.SUPPRESS)
        parser.add_argument('-U', '--user_name', nargs='+', help=argparse.SUPPRESS)
        parser.add_argument(
            '-q',
            '--quick',
            action='store_true',
            help="No logs from machine's var folder will be copied to host. No old core files will be checked and preserved",
        )
        parser.add_argument('-bringup_fast', '--bringup_fast', action='store_true', help=argparse.SUPPRESS)
        parser.add_argument(
            '-no_network_takedown',
            '--no_network_takedown',
            action='store_true',
            help="When selected skips deleting vnets during topology takedown. Make sure your new topology is using same vnets!",
        )
        parser.add_argument('-en', '--enable_nat', action='store_true', default=False, help=argparse.SUPPRESS)
        parser.add_argument('-ns', '--nosanity', action='store_true', help=argparse.SUPPRESS)
        parser.add_argument('-rv', '--rand_vpn', action='store_true', help=argparse.SUPPRESS)
        parser.add_argument('-ip', '--ignore_parallel', action='store_true', help=argparse.SUPPRESS)
        parser.add_argument('-us', '--update_stable_link', action='store_true', help=argparse.SUPPRESS)
        parser.add_argument('-scc', '--skip_comparing_of_configs', action='append', help=argparse.SUPPRESS)
        parser.add_argument('-encap', '--encap', action='store', default= 'ipsec', choices=['gre', 'gre_rest', 'ipsec', 'both'], help='Use this option to set encap type for tests')
        parser.add_argument('-tcp_opt', '--tcp_opt', action='store_true', help='Use this option to enable tcp-optimization on all service vpns for all vEdges')
        parser.add_argument('-bridge', '--bridge', action='store_true', help='Option to specify interface as part of bridge')
        parser.add_argument('-mcast', '--mcast', action='store_true', help='Option to enable multicast')
        parser.add_argument('-cellular', '--cellular', action='store_true', help='Converts ge0/0 to cellular0')
        parser.add_argument('-wlc', '--wlan_country', action='store', default= 'United States', help='Provide wlan options. Format: -wlc Country ')
        parser.add_argument('-brw', '--browser_options', action='append', default=[], help='Use this option to specify list of browsers. Ex: -brw chrome -brw safari')
        parser.add_argument('-ps', '--prepend_subtests', action='store', help='Use -ps <test_name> to prepend subtests of <test_name> to all tests in the run. Ex: -ps test_clear_statistics')
        parser.add_argument('-as', '--append_subtests' , action='store', help='Use -as <test_name> to append subtests of <test_name> to all tests in the run. Ex: -as test_tunnel_statistics')
        parser.add_argument('-nc', '--no_certificate', action='store_true', help='Brings up testbed with no certificate installed')
        parser.add_argument('-npc', '--no_parallel_cert', action='store_true', default= False, help='Set up certs in serial while testbed bringup')
        parser.add_argument('-vmp_old', '--vmanage_patch_old', action='store', help='Deprecated: vmanage patch file')
        parser.add_argument('-vmp', '--vmanage_patch', action='store', help='vmanage patch file')
        parser.add_argument('-csrp', '--csr_patch', action='store', help='*.bin file to patch CSR')
        parser.add_argument('-isrp', '--isr_patch', action='store', help='*.bin file to patch ISR')
        parser.add_argument('-ppp', '--ppp', action='store_true', help='Use this option to set transport interface to ppp type for tests')
        parser.add_argument('-sym_nat', '--enable_symmetric_nat', action='store_true', help='Configure Symmetric NAT')
        # The following 3 arguments are in bin/runner
        parser.add_argument('-ng', '--no-git', action='store_true', help='Do not use git to check out anything.')
        parser.add_argument('-stable', '--stable', action='store_true', help='Checkout and pull latest stable/next')
        parser.add_argument(
            '-gcb', '--git-checkout-branch', action='store', help='Checkout to specified branch and pull latest'
        )
        parser.add_argument(
            '-sku',
            '--sku',
            action='store',
            default='M',
            choices=['M', 'WM', 'M2'],
            help='Use this option to set sku type for tests',
        )
        parser.add_argument(
            '-wwan_sku',
            '--wwan_sku',
            action='store',
            default='VZW',
            choices=[
                'VZW',
                'ATT',
                'MC7354_GENERIC',
                'MC7304_GENERIC',
                'TELSTRA',
                'DOCOMO',
                'LTEUSB',
                'SPRINT',
                'GENERIC',
            ],
            help='Use this option to set wwan sku type for tests',
        )
        parser.add_argument(
            '-network_bw',
            '--network_bw',
            action='store',
            default='20',
            choices=['5', '10', '15', '20', 'ALL'],
            help='Use this option to set network bandwidth  type for tests',
        )
        parser.add_argument(
            '-serial_type',
            '--serial_type',
            action='store',
            default='T1',
            choices=['T1', 'E1', 'T3', 'E3'],
            help='Use this option to set the serial interface card type for T1E1 tests',
        )
        parser.add_argument(
            '-partner',
            '--partner_type',
            action='store',
            default=None,
            choices=['dnac', 'aci'],
            help='Use this option to set the partner type',
        )
        parser.add_argument(
            '-dual_tloc',
            '--dual_tloc',
            action='store',
            default='ethernet',
            choices=['ethernet', 'cellular'],
            help='Use this option to set dual tloc type for tests',
        )
        parser.add_argument(
            '-mtu_range',
            '--mtu_range',
            action='store',
            default='mtu_2k',
            choices=['mtu_2k', 'mtu_9k'],
            help='Use this option to set mtu_2k/mtu_9k type for tests',
        )
        parser.add_argument(
            '-snmpv3', '--snmpv3', action='store_true', help='Use this option to set the snmpv3 verion for tests'
        )
        parser.add_argument(
            '-github_status',
            '--github_status',
            action='store',
            default=None,
            help='Send status to given github endpoint',
        )
        parser.add_argument(
            '-github_comment',
            '--github_comment',
            action='store',
            default=None,
            help='Send comment to given github endpoint',
        )
        parser.add_argument('-qcow2', action='store_true', help='Download qcow2 images')
        parser.add_argument(
            '-so',
            '--suite-options',
            default=[],
            nargs='+',
            action='store',
            help='Any number of suite-specific options.'
            ' Do not use \'-\' for them\n'
            'Example of two options: -so vvu=/folder/foo evm',
        )
        parser.add_argument(
            '--prefer-local-images',
            action='store_true',
            help='Use local VM images, if present. Missing images will be downloaded.'
        )
        parser.add_argument(
            '--force-download-branch-images',
            action='store_true',
            help='Force download the newest images from Cisco repository instead of using statically defined in topology yaml file.',
        )
        parser.add_argument(
            '--force-topology-image-vms',
            action='store',
            default=None,
            help='Coma separated list of virtual machines for which images from topology file should be downloaded. For those machines flag "--force-download-branch-images" is ignored.',
        )
        parser.add_argument(
            '-dut_lux',
            '--dut_lux',
            nargs='?',
            const=True,
            default=None,
            type=str,
            help='If provided without a path, it acts as a boolean flag. If a path is provided, it uses the path for downloading image for dut. caveate single dut image can be provided',  # TODO: different platform DUT to be able to provide image
        )
        parser.add_argument(
            '-vcontainer',
            '--vcontainer',
            action='store_true',
            help='Use this option to set the vcontainer flag for tests',
        )
        parser.add_argument(
            '-mt',
            '--mt',
            action='store_true',
            default=False,
            help='Use this option to run vmanages of tb in multitenant mode',
        )
        parser.add_argument(
            '-mt_proxy',
            action='store_true',
            default=False,
            help='Use this option to run reverse proxy suite in multitenant mode',
        )
        parser.add_argument(
            '-selinux',
            action='store_true',
            default=False,
            help='SElinux denial checks on cEdge devices and copy the audit logs to /auto path',
        )
        parser.add_argument('-transport', '--transport', action='store_true', help='Use transport mode for rfc ipsec')
        parser.add_argument('-ikev1_aggressive', '--ikev1_aggressive', action='store_true', help='Use ikev1 aggressive mode for rfc ipsec')
        parser.add_argument('-ikev2', '--ikev2', action='store_true', help='Use ikev2 for rfc ipsec')
        parser.add_argument('-exclude_browser', '--exclude_browser', action='store_true', help='Exclude browser tests')
        parser.add_argument('-nb', '--no_bringup', action='store_true', help='Do not try to bringup testbed')
        parser.add_argument(
            '-no_caserver',
            '--no_caserver',
            action='store_true',
            help='Do not start ca server in multitenant ceriticate setup',
        )
        parser.add_argument(
            '-cisco_pki',
            '--cisco_pki',
            action='store_true',
            help='Cisco pki as ca server in multitenant certficate setup',
        )
        parser.add_argument('-uar', '--uar', action='store_true', help='Run Umbrella suite with auto registration')
        parser.add_argument('-pdc', '--pdc', action='store_true', help='Run PWK suite with pwk enabled only on vedges')
        parser.add_argument('-pdv', '--pdv', action='store_true', help='Run PWK with pwk enabled only on cedges')
        parser.add_argument(
            '-pdvc', '--pdvc', action='store_true', help='Run PWK with pwk diaabled on few cedges/vedges'
        )
        parser.add_argument('-pwka', '--pwka', action='store_true', help='Run PWK with pwk asymmetric rekey scheme')
        parser.add_argument(
            '-ent_certs',
            '--ent_certs',
            action='store_true',
            help='Set hardware wan edge certficate authorization as enterprise',
        )
        parser.add_argument('-proxy', '--reverse_proxy', action='store_true', help='enable proxy mode')
        parser.add_argument(
            '-cfg_sync',
            '--config_sync',
            action='store_true',
            help='enable checking of config-sync/side-effects' ' between confd and IOS, cedge specific only',
        )
        parser.add_argument('-ap', '--abort_parallel', action='store_true', help='abort parallel connection checks')
        parser.add_argument(
            '--logs_sub_dir', action='store', help='Directory name to store logs for this run. It is not full path'
        )
        parser.add_argument(
            '-utd_tar_image', '--utd_tar_image', action='store', default=None, help='Location of UTD tar image'
        )
        parser.add_argument(
            '-utd_tar_branch',
            '--utd_tar_branch',
            action='store',
            default=None,
            help='The utd tar branch from which image needs to be pulled (ex: 0.0/1.0)',
        )
        parser.add_argument(
            '-utd_profile',
            '--utd_profile',
            action='store',
            default='cloud-low',
            choices=['cloud-low', 'cloud-medium', 'onbox-low', 'onbox-medium', 'cloud-high', 'onbox-high'],
            help='Use this option to set utd profile for tests',
        )
        parser.add_argument(
            '-cflow_coverage', '--cflow_coverage', action='store_true', help='Collect cflow coverage data from cedges'
        )
        parser.add_argument(
            '-vsmoke', '--vsmoke', action='store_true', help='run vplatform smoke tagged cases with only VEDGE1 as DUT'
        )
        parser.add_argument(
            '-var_dict',
            '--var_dict',
            type=json.loads,
            default=None,
            help='Pass dictionary varibales to runner that can be used in the test scripts. Ex -var_dict \'{"vpn": "enable","appqoe":"enable", "tcpopt": "disbale"}\' ',
        )
        parser.add_argument(
            '-tt',
            '--test_traversal',
            action='store_true',
            help='Obsolete: Traverse tests prior to run and update test result after completion of each',
        )
        parser.add_argument('-dut', '--dut', action='store', default=None, help='Use to override DUTs from TTF')
        parser.add_argument(
            '-label',
            '--label',
            action='store',
            default=None,
            help='SElinux enblement for private images, specify the prviate image label',
        )
        parser.add_argument('-fw', '--fw_pkgs', default=None, help='modem firmware packages')
        parser.add_argument('-ux2', '--ux2', action='store_true', help='select UX2.0 for appqoe sanity/regression')
        parser.add_argument(
            '-vcc', '--vmanage_code_coverage', action='store_true', help='Enable jacoco code coverage for vManage'
        )
        parser.add_argument(
            '-ssr',
            '--enable-ssr-report-xml',
            action='store_true',
            help='Enable generation of ResultsDetails.xml used by SSR to generate run result table and charts',
        )
        parser.add_argument(
            "-cm",
            "--coverage_meta_data",
            const=os.environ.get('USER'),
            help="Collect coverage meta data for cEdge and vEdge (CTC++) and upload to the Cerebro "
            "(only for cEdge machines), please provide your user id with which you want Cerebro report to be generated. "
            "For example : -cm <userid> ",
            nargs='?',
        )

        # runsuite-added args
        parser.add_argument(
            '-lt',
            '--list-tests',
            action='store_true',
            help='List the chosen tests from the specified script/ttf.',
        )
        parser.add_argument('-nst', '--no-skip-tags', action='store_true', help='Don\'t skip any skip tags. (TODO)')
        parser.add_argument(
            '-rf',
            '--remove-functions',
            nargs='+',
            default=[],
            action='append',
            help='The default vm functions to exclude when determining which vms from the topology yaml to include. (TODO)',
        )
        parser.add_argument('-sd', '--scripts-dir', action='store', help='scripts directory if not tests/scripts.')
        parser.add_argument(
            '-sl',
            '--skip-legacy',
            action='store_true',
            help='Skip initializing ultimate',
        )
        parser.add_argument(
            '-st', '--skip-tags', nargs='+', action='store', help='Tags to skip. (TODO)', default=['skip']
        )
        parser.add_argument('-tf', '--tests-from', action='store', help='Start the testcases from testname/tag. (TODO)')
        parser.add_argument(
            '-til',
            '--tests-til',
            action='store',
            help='Start the testcases from the beginning until testname/tag. (TODO)',
        )
        parser.add_argument(
            '-vm',
            '--version-machine',
            action='store',
            default='',
            help='Name of machine from which to extract platform version.',
        )
        parser.add_argument(
            '-vt',
            '--version-machine-type',
            nargs='+',
            default=['cedge', 'vedge', 'vmanage'],
            help='Type of machine from which to extract platform version.',
        )

        parser.add_argument(
            '-slot',
            '--cellular_slot',
            default=None,
            help='Used for cellular commands on iosxe such as "show Cellular x/x/x", should be in the form "-slot 0/2/0"',
        )
        parser.add_argument(
            '-upgrade',
            '--upgrade_test',
            help='Used for upgrading the sdwan components, works with nosanity arg; image version could be specified using arguments -cvu,-vvu,-emu,-evu',
            action='store_true',
        )
        parser.add_argument(
            '-no_dtdash',
            '--no_dtdash_update',
            default=False,
            action='store_true',
            help='No logic on vTest side.'
            'Presence of this argument in command line is only for 3rd party tools that analyze vTest results',
        )
        parser.add_argument(
            '-nrdb',
            '--no_regressdb',
            default=False,
            action='store_true',
            help='Prevents any regressdb updates',
        )
        parser.add_argument(
            '-dvmv', '--default_vmanage_volume', default=None, help='Default vmanage volume/secodary memory size'
        )
        parser.add_argument(
            '-dvcv', '--default_vcontainer_volume', default=None, help='Default vcontainer volume/secodary memory size'
        )
        parser.add_argument(
            '-mte_vc', '--mtedge_vrf_count', action='store', help='Number of VRFs per tenant in MT-Edge topology'
        )
        parser.add_argument(
            '-mte_tm', '--mtedge_tenant_mode', action='store', help='Access vManage as tenant in MT-Edge topology'
        )
        parser.add_argument(
            '-mte_tr4', '--mtedge_trans_ipv4', action='store', help='Enable ipv4 on transport side in MT-Edge topology'
        )
        parser.add_argument(
            '-mte_sr4', '--mtedge_serv_ipv4', action='store', help='Enable ipv4 on service side in MT-Edge topology'
        )
        parser.add_argument(
            '-mte_tr6', '--mtedge_trans_ipv6', action='store', help='Enable ipv6 on transport side in MT-Edge topology'
        )
        parser.add_argument(
            '-mte_sr6', '--mtedge_serv_ipv6', action='store', help='Enable ipv6 on service side in MT-Edge topology'
        )
        parser.add_argument(
            '-crft',
            '--crft',
            default=False,
            action='store_true',
            help='Collect CRFT data',
        )
        parser.add_argument(
            '-no_crft_export',
            '--no_crft_export',
            default=False,
            action='store_true',
            help='Collect CRFT data and export to ads.',
        )
        parser.add_argument(
            '-crft_taas_export',
            '--crft_taas_export',
            default=False,
            action='store_true',
            help='Collects CRFT, uploads to /auto/polaris-storage and notifies TaaS',
        )
        parser.add_argument(
            '-btrace',
            '--btrace',
            default=False,
            action='store_true',
            help='Collect Btrace data',
        )
        parser.add_argument(
            '-thpt',
            '--qos_throughput',
            default='1000',
            action='store',
            help='UUT bandwidth for qos scripts, unit:Mbps, range from 50 to 100000',
        )
        parser.add_argument(
            '-stt',
            '--sig_tunnel_type',
            default='zscaler',
            action='store',
            help='Tunnel type for greatwall suites (zscaler/umbrella)',
        )
        parser.add_argument(
            '-ips_sig', '--ips_sig', action='store', default=None, help='Location of IPS signature package'
        )
        parser.add_argument(
            '-nssf',
            '--no_stop_on_setup_fail',
            action='store_true',
            default=False,
            help='Keep going even if a setup test fails. Implies --no_cleanup_setup_failure.',
        )
        parser.add_argument(
            '-ncsf',
            '--no_cleanup_setup_failure',
            default=False,
            action='store_true',
            help='Do not clean up device config if setup test cases fail.',
        )
        parser.add_argument(
            '-cc',
            '--cedge_cleanup',
            default=False,
            action='store_true',
            help='cleaup the cedge devices before the tesbed bringup',
        )
        parser.add_argument(
            '-update_tb',
            '--update_tb',
            action='store',
            help='Update testbed using addons/update_tb.py. Use \'all\' keyword for update all packages defined in addons/update_tb.py or apt comma-separated package(s) name(s)',
        )
        parser.add_argument(
            '--destroy_vnets',
            '-dvn',
            action='store_true',
            default=None,
            help='Clear all existing vnets. Exclusion list can be passed through -edvn (--exclude_destroy_vnets) switch.',
        )
        parser.add_argument(
            '--exclude_destroy_vnets',
            '-edvn',
            action='store',
            default=None,
            help='List of VM for which vnets will not be removed, e.g. edvn stcvm,vm10. This switch can be used only with -dvn (--destroy_vnets)',
        )
        parser.add_argument(
            '-lrc',
            '--log_running_config',
            action='store_true',
            help='log running-configuration before setup, after setup, before cleanup and after cleanup',
        )
        parser.add_argument(
            '-viv',
            '--vedge_image_version',
            action='store',
            help='vedge version to bringup the tb with',
        )
        parser.add_argument(
            '-bringup-start-dhcp',
            '--bringup_start_dhcp',
            action='store_true',
            default=None,
            help='Starts DHCP server before testbed bringup required for allocating MGMT IP to HW devices',
        )
        parser.add_argument(
            '-bringup-stop-dhcp',
            '--bringup_stop_dhcp',
            action='store_true',
            default=None,
            help='Stops DHCP server before testbed bringup used for allocating MGMT IP to HW devices',
        )
        parser.add_argument(
            '-dhcp-server-intf',
            '--dhcp_server_intf',
            action='store',
            default=None,
            help='Configured static IP to specific interface before starting DHCP server required for HW devices',
        )
        parser.add_argument(
            '-cleanup-start-dhcp',
            '--cleanup_start_dhcp',
            action='store_true',
            default=None,
            help='Starts DHCP server before testbed cleanup required for allocating MGMT IP to HW devices',
        )
        parser.add_argument(
            '-cleanup-stop-dhcp',
            '--cleanup_stop_dhcp',
            action='store_true',
            default=None,
            help='Stops DHCP server before testbed cleanup used for allocating MGMT IP to HW devices',
        )
        parser.add_argument(
            '-eanp',
            '--enable_auto_nego_pm',
            action='store_true',
            default=None,
            help='Enable auto negotiation for pms interfaces',
        )
        parser.add_argument(
            '-fips',
            action='store',
            nargs='?',
            const='all',
            default=None,
            help='Provide list of (or nothing for all) cedges on which FIPS mode should be enabled during bringup, e.g. -fips vm5,vm4 or -fips',
        )
        parser.add_argument(
            '-dsv',
            '--deploy_spirent_vm',
            action='store_true',
            default=None,
            help='Bringup spirent vm. It destroys vnets and existing stcvm and rebrings it up',
        )
        parser.add_argument(
            "-components",
            "--components",
            nargs="+",
            required=False,
            help="Optional: Provide Components for bugbuddy to run as list of names separated by spaces. For example, '-components vip-omp vip-vdaemon'",
        )
        parser.add_argument(
            '-dim',
            '--dynamic_interface_mapping',
            nargs='?',
            const=True,
            default=None,
            type=str,
            help='If provided without a path, it acts as a boolean flag. If a path is provided, it uses the path for interface mapping.',
        )
        parser.add_argument(
            '-sp',
            '--selinux-permissive',
            action='store_true',
            default=False,
            help='When True, enables logic arround setting SELinux mode to permissive when requesting IOSXE shell access',
        )
        parser.add_argument('--unid_platform', action='store', help='Uni-D platform name, e.g. C8500_12X')
        parser.add_argument(
            '--reserve_org_name',
            '-ron',
            action='store_true',
            default=False,
            help='Reserve an org-name for SDAVC suites to download cloud applications',
        )
        parser.add_argument(
            '--disable-profiling',
            action='store_true',
            default=False,
            help='Disable simple profiller',
        )

        parser.add_argument(
            '--enable-smart-tc-trace',
            '-smart',
            action='store_true',
            default=False,
            help='dtdash smart debug, enable testcase function trace',
        )
        parser.add_argument(
            '-cmem',
            '--collect_memory',
            default=False,
            action='store_true',
            help='Collect memory usage after every test, cedge specific only',
        )

        args = self.parse_args()

        args.build_number = args.additional  # runsuite compatibility
        self.branch = args.branch
        self.args = args
        self.vmanage_code_coverage = args.vmanage_code_coverage
        pref['no_lock'] = args.no_lock

        if args.documentation:
            print(self.get_suite_documenation(args.suite))
            return

        # first instantiation of GlobalParam singleton
        global_param = GlobalParam()
        global_param.selinux_permissive = args.selinux_permissive
        global_param.keep_image_checksums = args.keep_checksum_cache

        self.fw_pkgs = args.fw_pkgs
        self.cellular_slot = args.cellular_slot
        self.utd_tar_branch = args.utd_tar_branch
        self.utd_tar_image = args.utd_tar_image
        self.selinux = args.selinux
        self.bringup_fast = args.bringup_fast
        self.no_crft_export = args.no_crft_export
        self.crft = args.crft or args.crft_taas_export
        self.crft_taas_export = args.crft_taas_export
        self.btrace = args.btrace
        self.ips_sig = args.ips_sig
        self.enable_auto_nego_pm = args.enable_auto_nego_pm

        if args.getuser:
            self.username = input('vManage Username: ')
        else:
            self.username = 'admin'
        if args.getpass:
            import getpass
            self.password = getpass.getpass('vManage Password: ')
        else:
            self.password = 'admin'
        if args.force_generate:
            def purge(path):
                pattern = '.*bak'
                for f in os.listdir(path):
                    if re.search(pattern, f):
                        print("removed: " + os.path.join(path, f))
                        os.remove(os.path.join(path, f))

            purge(os.path.join(self.tests_dir, 'scripts'))
            purge(os.path.join(self.tests_dir, 'sessions'))
        if self.custom_args_parsing(parser, args) != 0:
            return 1
        self.ip = self.get_ip()
        self.coverage_meta_data = args.coverage_meta_data
        self.suite_name = args.suite
        self.upgrade_tag = self.upgrade_module = None
        self.upgrade_test = args.upgrade_test
        if self.upgrade_test:
            self.upgrade_tag = 'upgrade_sw'
            self.upgrade_module = 'tb_sw_upgrade'
        # Set whether ncclient debugs are on or off
        self.ncclient = args.ncclient_debug
        # Set whether our debugs are on or not
        self.debug = args.debug
        if args.run_remotely == 'CURRENT':
            args.run_remotely = None
        self.run_remotely = args.run_remotely

        self.logs_dir = pref.get("log_root") or os.path.join(self.tests_dir, 'logs')
        if not os.path.isdir(self.logs_dir):
            try:
                os.mkdir(self.logs_dir)
            except Exception as e:
                self.logger.warning("Cannot create logs_dir. Exception: {}".format(e))
        self.create_loggers(args.debug, args.remote, args.logs_sub_dir)
        self.tc_src_code_logger = TcSrcCodeLogging(self.logger)
        logs_cleaner = CleanLogsHandler()
        logs_cleaner.handle_request()

        self.summary = SummaryXML()
        self.summary.set_timestamp(self.timestamp)
        self.current_suite_name = ""
        # typettf_parser.TestCase()
        self.current_running_testcase = None

        vtest.init('runner', skips=['logging', 'environment'])
        args.logger = self.logger
        self.logger.debug('args string: %s' % self.args_string)
        self.logger.info('message: %s' % args.message)
        args.functions = []  # Placeholder, this is handled differently in runner
        args.tests_range = args.tags_range
        self.check_for_system_tb(args)
        self.scripts = self.get_scripts(args)
        scripts = [s[1] for s in self.scripts]  # only interested in middle value of (_, filepath, protocol_yaml)
        cert_validation.init()

        # Initialization includes loading suite modules
        args = self.common_init(scripts)

        # TODO: Where to call common_runner.close() ? Although it's not currently needed unless (until?)
        # ultimate gets instantiated by common_runner
        if self.args.list_tests:
            common_runner.list_tests(args)
            return 0
        self.test_def_file_path = str(self.args.ttf.ttf_path)
        if args.bringup_start_dhcp is not None:
            if args.bringup_start_dhcp:
                if args.dhcp_server_intf is None:
                    raise ValueError("DHCP server interface required for enabling DHCP server not specified.")
                else:
                    self.enable_disable_dhcp_server(True, args.dhcp_server_intf)
        elif args.bringup_stop_dhcp is not None:
            if args.bringup_stop_dhcp:
                if args.dhcp_server_intf is None:
                    raise ValueError("DHCP server interface required for disabling DHCP server not specified.")
                else:
                    self.enable_disable_dhcp_server(False, args.dhcp_server_intf)

        self.summary.set_command_args(self.args_string)

        if args.update_tb:
            linux_distro = platform.version().lower()
            if any([supported in linux_distro for supported in ['ubuntu', 'debian']]):
                self.logger.info("Updating testbed enviroment...")
                update_tb.install_required(custom_apt_pkgs=args.update_tb, log=self.logger)
            else:
                self.logger.warning("TB update not supported for distro: {}".format(linux_distro))

        self.debug_callback = DebugCallback(self)
        self.debug_callback.setup()

        self.ss = None
        self.valgrind = args.enable_valgrind
        self.keep_traffic_generation_alive = args.keep_traffic_generation_alive
        self.randomly_restart_daemons = args.randomly_restart_daemons
        self.disable_pm_console_logger = args.disable_pm_console_logger
        self.random_tloc_color = args.random_tloc_color
        self.identifier = args.identifier
        self.systopo = args.systopo
        self.message = args.message
        self.suite = args.suite
        #        self.include_vmanage = args.include_vmanage
        self.exclude_vmanage = args.exclude_vmanage
        self.include_vmanage = not self.exclude_vmanage
        if self.include_scaling_vmanage:
            self.include_vmanage = True
            self.exclude_vmanage = False
        self.vmanage_ips = args.vmanage_ips
        #self.mt_vmanage_ips = args.mt_vmanage_ips
        #if ip range is specified, create ips within range
        for ip in self.vmanage_ips:
            if '-' == ip[-2]:
                self.vmanage_ips.remove(ip)
                for num in range(int(ip[-3]), int(ip[-1])+1):
                    self.vmanage_ips.append(ip[:-3]+str(num))
        self.vmanage_version_compare = args.vmanage_version_compare
        self.transport_routing = not args.no_transport_routing
        self.transport_vpn = args.transport_vpn
        self.internal_nat = args.enable_internal_nat
        self.cflowd_transport_udp = args.enable_cflowd_transport_udp
        self.symmetric_nat = args.enable_symmetric_nat
        self.dpi = args.enable_dpi
        self.ech = args.enable_ciscohosted
        self.tls = args.tls
        self.nrcc = args.nrcc
        self.encap = args.encap
        self.var_dict = args.var_dict
        self.tcp_opt = args.tcp_opt
        self.ppp= args.ppp
        self.bridge = args.bridge
        self.mcast  = args.mcast
        self.cellular = args.cellular
        self.wlan_country = args.wlan_country
        self.trans_ipv6 = args.trans_ipv6
        self.ipv6_ra = args.ipv6_ra
        self.serv_ipv6 = args.serv_ipv6
        self.ipv6 = args.ipv6
        self.vsmart_policy_builder = args.vsmart_policy_builder
        self.ignore_parallel = args.ignore_parallel
        self.browser = args.browser_options
        self.no_certificate = args.no_certificate
        self.no_parallel_cert = args.no_parallel_cert
        self.sku=args.sku
        self.wwan_sku=args.wwan_sku
        self.network_bw=args.network_bw
        self.serial_type=args.serial_type
        self.partner_type=args.partner_type
        self.dual_tloc=args.dual_tloc
        self.mtu_range=args.mtu_range
        self.version_to_download = args.version_to_download
        self.non_dmz_ip = args.non_dmz_ip
        self.ubuntu_client_dns_resolver_ip = args.ubuntu_client_dns_resolver_ip
        self.edge_name_server_ip = args.edge_name_server_ip
        self.cxp_loss_percentage = args.cxp_loss_percentage
        self.secret_access_aws = args.secret_access_aws
        self.cxp_latency = args.cxp_latency
        self.cedge_version_upgrade = args.cedge_version_upgrade
        self.cedge_container_upgrade = args.cedge_container_upgrade
        self.vmanage_version_upgrade = args.vmanage_version_upgrade
        self.vedge_version_upgrade = args.vedge_version_upgrade
        self.aon_eio_version_upgrade = args.aon_eio_version_upgrade
        self.cedge_cleanup = args.cedge_cleanup
        self.ucs_cleanup = args.ucs_cleanup
        self.vedge_mips_upgrade = args.vedge_mips_upgrade
        self.image_to_download = args.image_to_download
        self.remote = args.remote
        self.runner_systb = None
        self.include_sec_vb23 = args.include_sec_vb23
        self.run_selenium_on_windows = args.windows
        self.snmpv3= args.snmpv3
        self.github_status_endpoint = args.github_status
        self.github_comment_endpoint = args.github_comment
        self.vcontainer=args.vcontainer
        self.mt_mode = args.mt
        self.mt_proxy = args.mt_proxy
        self.transport = args.transport
        self.ikev1_aggressive = args.ikev1_aggressive
        self.ikev2 = args.ikev2
        self.vmanage_patch_old = args.vmanage_patch_old
        self.vmanage_patch = args.vmanage_patch
        self.csr_patch = args.csr_patch
        self.isr_patch = args.isr_patch
        self.no_bringup = args.no_bringup
        self.no_caserver = args.no_caserver
        self.cisco_pki = args.cisco_pki
        self.uar = args.uar
        self.pdc =  args.pdc
        self.pdv =  args.pdv
        self.pdvc =  args.pdvc
        self.pwka =  args.pwka
        self.ent_certs = args.ent_certs
        self.reverse_proxy = args.reverse_proxy
        self.abort_parallel = args.abort_parallel
        self.config_sync = args.config_sync
        self.label = args.label
        self.utd_profile = args.utd_profile
        self.security_pid = ''
        self.cflow_coverage = args.cflow_coverage
        self.ssr = args.enable_ssr_report_xml
        self.quick = args.quick
        self.vsmoke = args.vsmoke
        self.ux2 = args.ux2
        self.mtedge_vrf_count = args.mtedge_vrf_count
        self.mtedge_tenant_mode = args.mtedge_tenant_mode
        self.mtedge_trans_ipv4 = args.mtedge_trans_ipv4
        self.mtedge_serv_ipv4 = args.mtedge_serv_ipv4
        self.mtedge_trans_ipv6 = args.mtedge_trans_ipv6
        self.mtedge_serv_ipv6 = args.mtedge_serv_ipv6
        self.qos_throughput = args.qos_throughput
        self.sig_tunnel_type = args.sig_tunnel_type
        self.no_cleanup_setup_failure = args.no_cleanup_setup_failure
        self.stop_on_setup_fail = not args.no_stop_on_setup_fail
        self.log_running_config = args.log_running_config
        self.reserve_org_name = args.reserve_org_name
        self.setup_done = False
        self.tests_done = False
        self.cleanup_done = False
        self.before_setup = False
        self.vedge_image_version = args.vedge_image_version
        self._tcs_summary = {}
        # Set of TC that had exception during updating it's results to DB
        # TC can be updated multiple times during run, but at the end
        # we want only single update, hence set without duplicated TC names
        self._tcs_update_errors = set()
        self.vmonitor = None
        self.components = args.components
        self.dynamic_interface_mapping = args.dynamic_interface_mapping
        self.unid_platform = args.unid_platform
        # enable smart debug, when testcase failed, capture the function trace
        SmartDebug.smart_debug(args.enable_smart_tc_trace)
        self.collect_memory = args.collect_memory

        if args.save_configs is not None:
            if len(args.save_configs) == 1:
                args.save_configs.append(None)
            res = self.save_current_configs(args.save_configs[0], args.save_configs[1])
            if args.suite is None:
                return res
        if args.load_configs and len(args.load_configs) > 0:
            if args.load_configs[0] == 'blank':
                res = self.back_to_base()
            else:
                if len(args.load_configs) == 1:
                    args.load_configs.append(None)
                res = self.load_specified_configs(args.load_configs[0], args.load_configs[1])
            if args.suite is None or res != 0:
                return res
        try:
            if args.remote is not None:
                #Submit a job to a remote server
                return self.run_remote_tests(args.remote, args.patch, args.suite, sys.argv[1:], args.vmanage_patch_old)
        except Exception:
            #Handle any erros that get thrown
            traceback.print_exc()
            return 1
        try:
            if args.local is not None and args.local:
                print("Running local patch")
                # Submit a job locally with a local patch
                return self.run_local_tests(
                    args.file_path, args.patch, args.suite, sys.argv[1:], args.vmanage_patch_old
                )
        except Exception:
            # Handle any errors that get thrown
            traceback.print_exc()
        self.tb_hostname = socket.gethostname().split('.')[0]
        res = self.check_suite_support(self.tb_hostname, args.suite)
        if res != 0:
            return res
        res = self.check_branch_support(self.tb_hostname, args.branch)
        if res != 0:
            return res
        self.test_suites = {}

        # database variables
        self.db_write = not args.no_regressdb
        self.db_wrote = False
        # self.db_exec_date = time.ctime()
        # self.db_search_date = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        jst_now = utc_now + datetime.timedelta(hours=16)
        self.db_exec_date = jst_now.strftime("%a %b %d %H:%M:%S %Y")
        self.db_search_date = jst_now.strftime('%Y-%m-%d %H:%M:%S')
        self.db_suite = ''
        self.db_build = ''
        self.db_build_id = ''
        self.db_test_suite_result = 'PASS'
        self.db_test_duration = ''
        self.db_core_found = ''
        self.db_log = ''
        self.db_url = ''
        self.regressdb_api_url = ''
        self.run_log = ''
        self.core_found = False
        self.script_crash = False
        self.db_test_suite = ''
        self.db_tb_name = ''
        self.spirent_failure = False
        #FIXME - end database variables
        self.logger.info(self.db_exec_date)
        self.server = False
        # yaml can contain "True" <- str or True <- bool, hence str() to unify them
        if str(pref.get('server', False)).lower() == 'true':
            self.server = True
        self.logger.debug('Server mode: %s', self.server)
        if args.verbose:
            self.logger.warning("The '--verbose' flag is deprecated and will be removed in a future version.")
        self.interactive = args.interactive
        self.logger.debug('Interactive mode: %s' % args.interactive)
        self.first_fail = args.stopatfail
        self.logger.debug('First fail mode: %s' % args.stopatfail)
        self.logger.debug('Cleanup mode: %s' % args.cleanup)
        self.no_nat = True
        self.warnings_list = []
        self.errors_list = []
        self.prompt = args.prompt
        self.skip_comparing_of_configs = args.skip_comparing_of_configs
        self.show_display = args.show_vmanage_gui
        self.qcow2 = args.qcow2
        self.additional = args.additional
        self.cedge_build = args.cedge_build
        self.cedge_branch = args.cedge_branch
        self.vedge_build = args.vedge_build
        self.different_image_type = args.different_image_type
        self.smu = args.software_maintenance_upgrade
        if args.level is not None:
            self.level = args.level
        else:
            try:
                if args.suite in self.get_suite_combinations():
                    self.level = pref['suites'][args.suite]['level']
                else:
                    raise KeyError
            except KeyError:
                try:
                    self.level = pref['default_level']
                except KeyError:
                    self.logger.error('ERROR: No default test level specified in the preference.yaml file')
                    return -1

        #Set whether the cdb needs to be cleared
        self.restart = args.fresh
        #Set if this job was submitted by a remote machine, means this is a server
        self.run_remotely = args.run_remotely
        #Set if a patch was supplied for a remote job
        self.patch = args.patch
        self.expect_logs = []
        #Add explainations for all these variables
        self.randomize = args.randomize
        self.recipient = args.user_name
        self.webex_id = pref.get('webex_id', '')
        self.test_stats = ""
        self.email = not args.no_email
        self.print_netconf = args.print_netconf
        self.http_debug = args.http_debug
        self.generate_configs = args.generate_configs
        self.load_configs = args.load_configs
        if type(self.load_configs) == list and len(self.load_configs) == 0:
            self.load_configs = True
        self.root_sessions = {}
        self.ncs_sessions = {}
        self.enable_short_rekey = args.enable_short_rekey
        self.exclude_systembed = ['system2', 'system102']

        self.check_for_system_tb(args)

        # log env variables (if any) that specify images paths to be used during TB creation
        self.log_env_variables(pattern='TB_')
        self.store_pref_in_file()
        self.log_args_with_help(parser)

        self.tests_in_suite = 0
        self.testcase_fail_count = 0
        self.number_of_test_cases = 0
        self.profiler = create_profiler(Paths().current_logs() / 'vtest' / 'profiling', not self.args.disable_profiling)

        if args.testcase_timeout != TimeoutTCException.tout_default_val:
            ret = TimeoutTCException.set_tout_val(args.testcase_timeout)
            if not ret:
                self.logger.warning(
                    "Problem with settig tescase timeout [from CLI] value of: {}".format(args.testcase_timeout)
                )

        self.logger.info("Using test case timeout value: {}".format(TimeoutTCException.get_tout_val_human()))

        self.results = TestStats()
        try:
            #Run all the tests
            return self.run_tests()
        except (Exception, SystemExit):
            # Handle any exceptions that get thrown and print a custom stack trace
            # Handle SystemExit that maybe thrown from TC code
            self.logger.info(traceback.format_exc())
            return
        finally:
            if self.results.passed == 0:
                self.db_test_suite_result = 'FAIL'

            # if there are any TCs left with NOT_RUN status , mark whole suite as FAILED.
            # It can happen when run will be stopped by TC code raising SystemExit.
            for tc_name, tc_v in self._tcs_summary.items():
                if TCResult.NOT_RUN == tc_v[TEST_INFO_INDEX_OF_TC_RESULT]:
                    self.logger.error("TC {} has unexpected-initial result of {}.".format(tc_name, TCResult.NOT_RUN))
                    self.logger.info(
                        "Marking whole suite result as FAIL from previous value of {}".format(self.db_test_suite_result)
                    )
                    self.db_test_suite_result = 'FAIL'
                    # propagate suite FAIL status to summary.xml
                    self.test_suites[self.current_suite_name].set('result', 'fail')
                    self.summary.save()
                    break

            run_time = int(time.time() - self.start)
            # Close all expect sessions and their logs
            # This was moved here since we want to close / remove empty files from log (not to copy them)
            self._cleanup()
            bugbuddy_status = self.bugbuddy_util.get_status()
            self.bugbuddy_util.log_state(self.logger)
            if self.db_write and self.db_build_id:
                try:
                    with self.get_db_client() as db_handle:
                        db_handle.update_suite_to_db(
                            self.db_build_id,
                            self.results.total_tests,
                            self.results.total_subtests,
                            self.results.failed_subtests,
                            testsuiteresult=self.db_test_suite_result,
                            suiteduration=str(datetime.timedelta(seconds=run_time)),
                            core_found=self.db_core_found,
                            bugbuddy_status=bugbuddy_status,
                            numpassed=self.results.passed,
                            numfailed=self.results.failed,
                            numerrored=self.results.errored,
                            numskipped=self.results.skipped,
                            numaborted=self.results.aborted,
                            numblocked=self.results.blocked,
                        )
                except Exception:
                    self.logger.warning("Failed to update test status in the DB", exc_info=True)

            # Backing up logs after last DB update from the above just in case any SQL errors are present
            if self.db_write:
                self._backup_logs()
            else:
                self.logger.warning("no_regressdb flag is set: log backup skipped")

            try:
                # Create tar.gz with all vm/pm dirs
                self.create_machine_log_tar()
            except Exception as e:
                self.logger.error("create_machine_log_tar():\n{}".format(str(e)))

            # send signal to vmonitor that we've reached the end of execution
            if self.vmonitor:
                send_signal_to_vmonitor(self.logger, self.vmonitor)

            if hasattr(self, 'tb'):
                self.tb.stop_monitor(False)
            self.stop_loggers()
            list_all_threads_and_processes(self.logger)

            return RunnerExitCode.SUCCESS if self.db_test_suite_result == 'PASS' else RunnerExitCode.GENERIC_FAILURE

    def parse_args(self):
        args = self.parser.parse_args()
        if args.ipv6:
            args.serv_ipv6 = True
            args.ipv6_ra = True

        if args.ipv6_ra:
            args.trans_ipv6 = True
        if args.include_vs4:
            self.include_vs4 = True
            args.include_vs3 = True
        else:
            self.include_vs4 = False
        if args.include_vs20:
            self.include_vs20 = True
            args.include_vs3 = True
            args.include_vs4 = True
        else:
            self.include_vs20 = False
        if args.include_scaling_vmanage:
            self.include_scaling_vmanage = True
        else:
            self.include_scaling_vmanage = False
        if args.include_scaling_vmanage6:
            self.include_scaling_vmanage = True
            self.include_scaling_vmanage6 = True
        else:
            self.include_scaling_vmanage6 = False
        return args

    def common_init(self, scripts):
        self.args.logger = self.logger  # FIXME(common runner): args is stuffed with logger
        self.args.functions = []
        self.logger.debug('calling common_runner.init')
        # Suite modules will have a chance to influence vtest configuration, including modifying
        # the command line, so cache the args before re-getting them now.
        original_args = self.args
        original_branch = original_args.branch  # XXX cases.upgrades updates args, but shouldn't
        common_runner.init(self.args, scripts)
        self.logger.debug('calling common_runner.init DONE')
        self.args = self.parse_args()  # re-getting the args
        args_string = ' '.join(sys.argv[1:])
        if args_string != self.args_string:
            self.args_string = args_string
            self.logger.debug('modified args string: %s' % self.args_string)
        self.args.tests_range = original_args.tags_range  # common runner uses `tests_range`
        self.args.build_number = original_args.additional  # runsuite compatibility

        # Restore variables stuffed in the args object by common runner
        # FIXME
        self.args.logger = original_args.logger
        self.args.ttf = original_args.ttf
        self.args.ultimate = original_args.ultimate
        self.args.modules = original_args.modules
        self.args.functions = original_args.functions
        self.args.suite_options = original_args.suite_options

        # Restore runner cached args (this is a hack because we know what args changed,
        # we can't rely on this hack long term)
        self.branch = self.args.branch
        self.additional = self.args.additional
        if not self.branch:  # if it wasn't passed on the command line
            version = get_testbed_version(default=DEFAULT_BRANCH, build=self.additional)
            self.branch = self.args.branch = version.branch
            self.additional = self.args.additional = version.build
        if self.branch != original_branch:
            # args.branch was cached before modules initialized by common_init apparently
            # changed things. However, this is only necessary on a new testbed bringup.
            if self.args.new_testbed is not None:
                reload_preference(SdwanVersion(self.branch).branch)
        diffs = diff_namespaces(original_args, self.args)
        self.logger.debug(f'Args that changed after common init:\n{pformat(diffs)}')
        return self.args

    def check_for_system_tb(self, args):
        # if a yaml_file was provided, check if it points to a system tb and establish environment accordingly
        self.runner_systb = None
        if not args.yaml_file:
            return
        if '/' in args.yaml_file:
            yaml_file = args.yaml_file.split('/')[-1]
        else:
            yaml_file = args.yaml_file
        if yaml_file.endswith('.yaml'):
            yaml_file = yaml_file.split('.yaml')[0]
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        yaml_dir = os.path.join(base_dir, 'yamls')
        yaml_path = os.path.join(yaml_dir, 'topology', 't%s.yaml' % yaml_file)
        proto_path = os.path.join(yaml_dir, 'protocols', 'p%s.yaml' % yaml_file)
        if os.path.isfile(yaml_path):
            self.logger.debug('Yaml file exists')
            with open(yaml_path, 'r') as f:
                yp = yaml.safe_load(f)
                f.close()
            if 'system_tb_host' in yp:
                self.logger.debug('System testbed identified, System execution mode')
                # runner_systb - list containing systembed name, name of control host, ip of control host
                self.runner_systb = list([yp['system_tb_host']['tb_name']])
                self.runner_systb.append(yp['system_tb_host']['hostname'])
                self.runner_systb.append(yp['system_tb_host']['ip'])
                self.tb = Testbed(base_dir, False, False, None, self.runner_systb)
                self.tb.clear_handlers()
                self.api = Tests(proto_path, [])
            else:
                self.runner_systb = None
        else:
            self.logger.info('Yaml file not found in sys-tb check, continuing without it')

    def store_pref_in_file(self):
        f_name = 'pref.log'
        if pref is None:
            self.logger.warning('Problem with saving pref as pref is None')
            return
        try:
            path = self.logs_sub_dir + "/" + f_name
            with open(path, 'w') as f:
                f.write(str(json.dumps(pref, indent=4)))
        except Exception as e:
            self.logger.warning('Problem with saving pref as {}, exception is :\n{}'.format(path, str(e)))

    def log_env_variables(self, pattern=''):
        '''
        This function will create log entry with env variables for easier debugging.
        If pattern is specified and matched with env key, INFO level message will be logged.
        '''
        for ek, ev in os.environ.items():
            if pattern and pattern in ek:
                self.logger.info("os.environ[{}]={}".format(ek, ev))

    def _backup_logs(self):
        """Perform logs backup"""
        global runner_keyboard_interrupted
        if runner_keyboard_interrupted:
            msg = "Log backup skipped due to ctrl+c detected"
            self.logger.warning(msg)
            if self.db_build_id:
                try:
                    with self.get_db_client() as db_handle:
                        db_handle.update_blogs_to_db(self.db_build_id, "", msg)
                except Exception as e:
                    self.logger.error(f"Error updating regressDB with {msg!r} message:\n{e}")
            return

        if self.db_build_id:
            try:
                msg = "Log backup in progress..."
                with self.get_db_client() as db_handle:
                    db_handle.update_blogs_to_db(self.db_build_id, "", msg)
            except Exception as e:
                self.logger.error(f"Error updating regressDB with {msg!r} message:\n{e}")

        # LogBackup will handle case if self.db_build_id is None (will use timestamp)
        log_backup = LogBackup(self.db_build_id, self.logs_sub_dir, self.timestamp, self.logger, self.tb_hostname)
        log_backup.run()

        try:
            with self.get_db_client() as db_handle:
                log_backup.update_db(db_handle)
        except Exception as e:
            self.logger.error("There was following problem with log_backup.update_db(db_handle):\n{}".format(str(e)))

    def get_db_client(self):
        if not self.db_write:
            self.logger.warning("Called self.get_db_client(), but self.db_write is False")
        if self.db_build_id is None:
            self.logger.warning("Called self.get_db_client(), but self.db_build_id is None")

        if not pref.get("rest_db_client"):
            return sqldb.Sqldb()
        else:
            return sqldb_rest.SqldbRest(pref.get("db_rest_client_url"))

    @staticmethod
    def skip_due_to_subtests_structure(tc_name, subtests):
        # type: (str, vtyping.TestSteps) -> None
        if not any(isinstance(subtest, (list, tuple)) and callable(subtest[0]) for subtest in subtests):
            raise SkippedTCException("{} is marked as 'SKIPPED'. TC didn't return any callable objects".format(tc_name))

    def get_ip(self):
        IP = "127.0.0.1"
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.239.136.11", 80))
            IP = s.getsockname()[0]
        finally:
            s.close()
        return IP

    def custom_args_parsing(self, parser, args):
        """
        Deals with the parsing of those argument combinations which argparse
        cannot handle

        @params
            - parser: instance of argparse.ArgumentParser(), used to print
                      usage in case of a failure
            - args: parsed args from "parser"
        @return
            returns zero on success and a non-zero value in case of a failure
        """
        if args.branch is None:
            if args.new_testbed:
                option = '-n/--new_testbed'
            elif args.remote:
                option = '-r/--remote'
            elif args.run_remotely:
                option = '-R/--run_remotely'
            else:
                option = None
            if option:
                parser.print_usage()
                print('runner: error: -b/--branch is required with %s' % option)
                return 1

        if args.suite is None:
            if not args.save_configs and not args.load_configs:
                parser.print_usage()
                err_msg = 'runner: error: '
                err_msg += 'either one of suite, save_configs or load_configs '
                err_msg += 'must be specified'
                print(err_msg)
                return 1
        if args.save_configs is not None and len(args.save_configs) > 2:
            parser.print_usage()
            err_msg = 'runner: error: -sc/--save_configs cannot have more then 2 args'
            print(err_msg)
            return 1
        if args.load_configs != False and len(args.load_configs) > 2:
            parser.print_usage()
            err_msg = 'runner: error: -lc/--load_configs cannot have more then 2 args'
            print(err_msg)
            return 1
        return 0

    def _cleanup(self):
        if self.message is not None and "qualify_build_" in self.message:
            # this change was done for Ninad
            if (self.results.total_subtests > 0) and (self.results.failed_subtests == 0):
                subprocess.call('echo pass > /tmp/%s' %self.message, shell = True)
            else:
                subprocess.call('echo fail > /tmp/%s' %self.message, shell = True)
        if self.results.failed == 0 and self.results.executed > 0:
            if self.remote:
                remotely_submitted_file = os.path.join(os.getenv("HOME"), 'images', self.remote)
                if os.path.isfile(remotely_submitted_file):
                    self.logger.info("Removing file: {}".format(remotely_submitted_file))
                    os.remove(remotely_submitted_file)
        #Check to see if the ultimate dictionary exists, if it doesn't then there is nothing to clean up
        try:
            self.ultimate
        except AttributeError:
            return
        vgs = self.ultimate.get('vgs', None)
        if vgs is not None:
            vgs.exit_browser()

        for session in self.session_wrappers():
            self.logger.debug("%s.clean_up()", session.__class__.__name__)
            session.clean_up()

        # ps = self.ultimate.get('ps', None)
        # if ps is not None:
        #     ps.stop_display()
        #     ps.stop_webdriver(ps.webdriverProcess)

        #Delete http cookie files
        self.delete_all_http_cookie_files()
        #Delete http cookie files
        self.delete_all_temp_js_files()
        #Copy the console logger logs for hardware nodes
        self.copy_console_logger_logs()
        if not self.keep_traffic_generation_alive:
            #If we have a spirent session then close it
            if self.ss is not None:
                if self.ultimate['ss'].stc is not None:
                    try:
                        self.ultimate['ss'].disconnect_from_test_session(True)
                    except Exception:
                        self.logger.warning('Could not find spirent session to disconnect, skipping this step.')
                        pass
        if self.ixias is not None:
            self.ixias.__del__()
        if self.ubuntu is not None:
            self.ubuntu.__del__()
        if self.ise is not None:
            self.ise.__del__()
        if self.ad is not None:
            self.ad.__del__()
        res = self.close_all_machine_sessions()
        self.tb.stop_monitor(False)
        try:
            self.tb.__del__()
        except Exception:
            pass
        return res

    def delete_dir_contents(self, top):
        """recursively delete all dirs and files from root path"""
        if top != '/': #Do not run if root is specified
            for root, dirs, files in os.walk(top, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))

    def delete_all_http_cookie_files(self):
        cookie_dir = str(Paths().vtest('http_cookies'))
        self.delete_dir_contents(cookie_dir)

    def delete_all_temp_js_files(self):
        temp_js_dir = str(Paths().scripts('protractor/configs'))
        self.delete_dir_contents(temp_js_dir)

    def close_all_machine_sessions(self):
        #For each session close the expect session and its log file
        p = []
        queue_length = 0
        for session in list(self.ultimate['sessions'].keys()):
            queue_length += len(self.ultimate['sessions'][session])
        q = queue.Queue(queue_length)
        #For each session close the expect session and its log file
        for session_type in list(self.ultimate['sessions'].keys()):
            for machine in self.ultimate['sessions'][session_type]:
                #TODO: Check with Achar, Rauf
                if self.tb.is_cedge(machine):
                    continue
                all_args = (self.close_session, (machine, session_type), q)
                proc = Thread(target = self.call_func_as_process, args = all_args)
                proc.start()
                p.append(proc)
        #Wait for all the threads to get done
        for proc in p:
            proc.join()
        #Get the results from the queue
        res = 0
        while q.empty() is False:
            res += q.get()
        return res

    def close_session(self, machine, session_type='confd'):
        try:
            if machine in list(self.ultimate['sessions'][session_type].keys()):
                self.ultimate['sessions'][session_type][machine].close()
                if self.ultimate['sessions'][session_type][machine].logfile != sys.stdout:
                    self.ultimate['sessions'][session_type][machine].logfile.close()
        except AttributeError:
            pass
        except KeyError:
            print(self.ultimate['sessions'][session_type])
        except Exception:  # No reason to crash when closing out a session so catch all
            # This seems to happen when there is a pexpect timeout:
            # pexpect.exceptions.ExceptionPexpect: isalive() encountered condition where "terminated" is 0,
            # but there was no child process. Did someone else call waitpid() on our process?
            pass
        return 0

    def special_tags(self, tags, oper = 0):
        """
        Returns boolean dictating whether the passed tags are specal values as
        defined in the preference.yaml file

        @params
            - tags: a list of tags that need to be checked
            - oper: val of 0 means 'or', equivalent to "is any of the tags a
                    special tag"
                    val of 1 means 'and', equivalent to "are all of the tags
                    special tags"
        @return
            bool
        """

        #The argument tags is expected to be a list
        #oper 0 is or, meaning is any of the tags a special tag
        #oper 1 is and, meaning are all of the tags special tags
        try:
            special_tags = pref['special_tags']
        except KeyError:
            special_tags = [None]
        if oper == 0:
            return not set(tags).isdisjoint(set(special_tags))
        elif oper == 1:
            return set(tags) > set(special_tags)

    def create_machine_log_tar(self, output_file="admin_tech.tar.gz"):
        """Gets all dirs with machine logs (i.e. vm*, pm*) and add it to [output_file].tar.gz"""
        f = os.path.join(self.logs_sub_dir, output_file)
        self.logger.info('Creating tar.gz file (%s) for all vm/pm logs.', f)
        saved_dir = os.getcwd()
        os.chdir(self.logs_sub_dir)
        dirs_to_tar = [match for match in glob.glob("[v|p]m*") if os.path.isdir(match)]
        with tarfile.open(output_file, "w:gz") as tarhandle:
            for cnt, dir_to_tar in enumerate(dirs_to_tar, start=1):
                self.logger.debug("[create_machine_log_tar] {} of {}".format(cnt, len(dirs_to_tar)))
                tarhandle.add(dir_to_tar)
        os.chdir(saved_dir)
        self.logger.info('Creating tar.gz file (%s) for all vm/pm logs done.', f)

    def get_topology_yaml_from_ttf(self, ttf_file_path):
        topology_file_path = None
        try:
            with open(ttf_file_path) as ttf_file:
                ttf_content = ttf_file.read()
                match = re.search('topology[ ]*=[ ]*[\'\"](.*)[\'\"]', ttf_content)
                if match:
                    topology = match.group(1)
                    if topology:
                        if os.path.isfile(topology):
                            topology_file_path = topology
                        else:
                            ttf_dir = os.path.dirname(ttf_file_path)
                            relative_path = os.path.join(ttf_dir, topology)
                            if os.path.isfile(relative_path):
                                topology_file_path = relative_path
                            else:
                                vtest_topology_dir = '%s/yamls/topology' % os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                                vtest_topology_path = os.path.join(vtest_topology_dir, "{}.yaml".format(topology))
                                if os.path.isfile(vtest_topology_path):
                                    topology_file_path = vtest_topology_path
        except Exception as ex:
            self.logger.exception(ex)
        finally:
            return topology_file_path

    def clean_dat_files(self):
        for machine in self.tb.machines():
            if self.tb.is_cedge(machine):
                self.ultimate['iosxe'].exec_cmd_in_binos(machine, '/usr/bin/cflow clear', 180)

    def get_scripts(self, args):
        '''
        Returns a list of lists.

        Each list item is itself a list of 3 str items, in this order:

        1. Ttf name (ie, suite) specified as first argument on runner command line
        2. Full path of a TTF file, not necessarily the one in #1, for example, the full path of test_sanity.ttf, when
           the `-ns` flag is not used.
        3. The protocol yaml name specified as a second optional runner argument without a flag.

        Example Return value (spacing added to avert pre-check):
        ```python
        [
            ['cEdgeFIT', '/home / tester / vtest/tests/scripts/test_sanity.ttf', None],
            ['cEdgeFIT', '/home / tester / vtest/tests/scripts/test_cEdgeFIT.ttf', None]
        ]
        ```
        '''

        # Check if the suite is one of the predefined suites, meaning either one of the scripts or the suite combinations defined in the preference.yaml file
        scripts = []
        if args.suite in self.get_all_scripts():
            # If no tags are specified or if a special tag is specified and we are not in prompt
            # mode and the nosanity flag is not specified and we're not running a system bed, run
            # sanity before any other suite
            no_sanity = (len(args.tags) != 0) and (not self.special_tags(args.tags))
            no_sanity = no_sanity or (args.tags_range is not None)
            no_sanity = no_sanity or args.nosanity
            no_sanity = no_sanity or self.runner_systb is not None
            no_sanity = no_sanity or self.args.prompt
            proto = [] if no_sanity else ['sanity']
            # If the suite is one of the combinations then figure out which suites to run, else just run the specified suite
            if args.suite in self.get_suite_combinations():
                proto += self.get_suite_combinations(args.suite)
            else:
                proto += [args.suite]
            if 'ztp' in proto and not Machines().get_vmanage():
                proto.remove('ztp')
            no = 0
            # For each suite in proto list get the absolute path for the script
            for item in proto:
                no += 1
                protocol_list = item.split(' ')
                if len(protocol_list) == 2:
                    protocol_yaml = protocol_list[1]
                else:
                    protocol_yaml = args.yaml_file
                protocol = protocol_list[0]
                if protocol == 'sanity':
                    if self.args.generate_configs:
                        continue
                    protocol = proto[no]
                file_path = f'{self.tests_dir}/scripts/test_{protocol_list[0]}.ttf'
                scripts.append([protocol, file_path, protocol_yaml])
        # If the suite is not one of the predifined suites assume args.suite is the path to the script to be run
        else:
            script_dir = os.path.realpath(os.path.dirname(args.suite))
            protocol = os.path.basename(script_dir)
            scripts.append([protocol, args.suite, args.yaml_file])
        # Update the list of suites to run based on the args.count variable value
        count = int(args.count if args.count is not None else pref.get('count', 0))
        if count:
            if args.suite not in self.get_suite_combinations() and len(scripts) > 1:
                scripts = scripts + scripts[1:] * count
            else:
                scripts = scripts * count
        return scripts

    def bind_testcase(self, test_case, script_path):
        try:
            module = SuiteModules().get_suite_module(test_case.module_name).lib
        except Exception:
            # Not expected to happen but print the stack if it does for analysis
            self.logger.debug(traceback.format_exc())
            module = import_module(test_case.module_name)
        try:
            test_func = getattr(module, test_case.name)
        except AttributeError:
            self.logger.error(
                "TTF testcase definition invalid: {}, module {} does not contain method {}! Please update or remove invalid line from TTF file {}".format(
                    test_case, module, test_case.name, script_path
                )
            )
            raise
        if test_func is None:
            self.logger.error(
                "TTF testcase definition invalid: {}, module {} attribute {} is None. Skipping this test case from {}".format(
                    test_case, module, test_case.name, script_path
                )
            )
            raise Exception("Test function {} in module {} is None".format(test_case.name, module))
        test_case.function = test_func

    def run_tests(self):
        """
        Runs all test functions in all the specified suites
        """
        args = self.args
        trace = False
        if self.prompt:
            self.version_checked = True
            args.quick = True
        else:
            self.version_checked = False
        if args.no_lock:
            testbed = os.path.join(self.logs_sub_dir, "testbed")
            os.mkdir(testbed)

            self.topology_yaml = args.yaml
            with open(self.topology_yaml, 'r') as topology_yaml_file:
                topo = yaml.safe_load(topology_yaml_file)
                tbstate = {'branch': self.branch, 'since': time.strftime("%Y-%m-%d %H:%M:%S"), 'status': 'up'}
                for machine_name in topo['machines']:
                    tbstate[machine_name] = 'up'
                with open(os.path.join(testbed, "state.yaml"), 'w') as state_file:
                    yaml.dump(tbstate, state_file)
                if args.terraform_state:
                    terraform_state_path = os.path.abspath(args.terraform_state)
                    topo = config_utils.setup(topo, terraform_state=terraform_state_path)

                with open(os.path.join(testbed, "config.yaml"), 'w') as config_file:
                    config_file.write(yaml.safe_dump(topo))

            self.tb = Testbed(testbed)
            Machines.register(self.tb.config, self.logger, os.path.join(testbed, "config.yaml"))
        else:
            hostname = os.uname()[1] if self.runner_systb is None else self.runner_systb[1]
            self.lock = vLock(hostname=hostname)

            testbed = self.get_testbed()
            #If this is a remote run and there is alread a testbed up take down that testbed
            if self.run_remotely is not None and testbed is not None:
                tb = HyperVisor(testbed)
                tb.clear_handlers()
                if self.valgrind:
                    self.logger.info('Disabling valgrind')
                    tb.disable_valgrind()
                start_time = time.time()
                tb.takedown()
                self.logger.info('Time taken to takedown testbed: %s' % str(datetime.timedelta(seconds=(int(time.time()) - int(start_time)))))
            #Set 'testbed' to the name of the new testbed that needs to be created
            testbed = args.new_testbed
            #If we are not going to create a new testbed see if there is an existing one that needs to be upgraded
            if testbed is None:
                testbed = args.upgrade
            #If we are not going to create a new testbed then get the current testbed
            if testbed is None or testbed == '':
                testbed = self.get_testbed()
                #If there is no current testbed then raise an error and exit
                if testbed is None:
                    self.logger.error(self.error('No testbed is up'))
                    return 1
            #Create an instance of the testbed that we are going to use
            self.tb = HyperVisor(testbed, self.debug, args.rand_vpn, trans_ipv6=self.trans_ipv6, ipv6_ra=self.ipv6_ra, serv_ipv6=self.serv_ipv6, log_root=self.logs_sub_dir)
            self.tb.clear_handlers()
            self.tb.purge()

        #vm23 vbond2 is required by default in following suites
        if self.suite in ['vdaemon', 'ipsec', 'vdaemonv4v6']:
            self.include_sec_vb23 = True
            args.include_sec_vb23 = True
        self.logger.info('Suite: ' + args.suite)
        git_branch = misc.get_git_branch()
        self.logger.info('Git branch: {}'.format(git_branch))
        if git_branch and "Not a git repo" not in git_branch:
            git_commit_info = misc.get_latest_git_commit_info()
            self.logger.info('Git commit hash: {}'.format(git_commit_info[0]))
            self.logger.info('Git commit date: {}'.format(git_commit_info[1]))
        if not self.bugbuddy_util.bug_buddy_missing:
            git_bugbuddy_branch = misc.get_bugbudy_git_branch()
            self.logger.info('[BugBuddy]: Git branch: {}'.format(git_bugbuddy_branch))
            git_bugbuddy_commit_info = misc.get_latest_bugbuddy_git_commit_info()
            self.logger.info('[BugBuddy]: Git commit hash: {}'.format(git_bugbuddy_commit_info[0]))
            self.logger.info('[BugBuddy]: Git commit date: {}'.format(git_bugbuddy_commit_info[1]))
        self.logger.info('Testbed: ' + os.path.basename(self.tb.workdir))
        self.db_tb_name = os.path.basename(self.tb.workdir)

        #If we are not starting in prompt mode and the no_email flag has not been specified then send a start email
        if self.prompt is False and self.email:
            #The send_email function figures out whether we are running on a server or not. Based on that it stores
            #the results in a the regressdb. It also sends an email if the -U option was specified
            self.store_results('start', tags = args.tags, message = args.message)
        force_topology_image_vms = (
            args.force_topology_image_vms.split(",") if args.force_topology_image_vms is not None else []
        )

        # If the ucs cleanup flag was specified then use the ansible script to cleanup the testbed
        if args.ucs_cleanup:
            self.logger.info("***** UCS CLEANUP ******")
            UCSHost().ucs_cleanup()
            self.logger.info("***** Done - UCS CLEANUP ******")
        if args.deploy_spirent_vm and args.overwrite and args.new_testbed:
            self.logger.info("***** Spirent VM bringup ******")
            self.tb.bringup_spirent_vm()
            self.logger.info("***** Done - Spirent VM bringup ******")
        if args.new_testbed is not None:
            retval = None
            duration = -1
            self.logger.debug('Creating testbed')

            if isinstance(args.fips, str):
                self.tb.enable_fips = args.fips.split(",")

            if self.tb.is_kvm_tb():
                self.tb.destroy_all_vnets = args.destroy_vnets
                self.tb.destroy_all_vnets_exclude = (
                    args.exclude_destroy_vnets.split(",") if args.exclude_destroy_vnets is not None else []
                )
                self.tb.destroy_all_vm_vnets()
                self.tb.reserve_org_name = args.reserve_org_name
                self.tb.auto_reserve_org_name((args.suite, self.db_build_id))

            if args.yaml is not None:
                self.topology_yaml = args.yaml
            else:
                self.topology_yaml = self.get_topology_yaml_from_ttf(self.test_def_file_path)
            #Use the default yaml file, viptela.yaml, unless a different one is specified
            if not self.topology_yaml:
                self.topology_yaml = 'default'

            if self.run_remotely is not None:
                #If a patch file was given then use the information specified in the patch file to create a new testbed
                if self.patch is not None or self.vmanage_patch_old is not None:
                    if self.patch is not None:
                        patch = self.patch
                    else:
                        patch = 'vmanage'
                    try:
                        retval = self.tb.patch(None, None, patch, False, self.run_remotely, args.overwrite, self.topology_yaml, args.exclude_vmanage, args.include_hdp, args.include_vs3, args.include_sec_vb23, args.include_vs4, args.include_scaling_vmanage, args.include_vs20, args.include_scaling_vmanage6, args.include_tlocExt_gre)
                    except Exception as err:
                        self.send_status_to_github_endpoint('failure')
                        self.send_comment_to_github_endpoint('failed to patch testbed')
                        self.db_test_suite_result = 'FAIL'
                        self.db_core_found = 'Patch failed'
                        self.logger.error(err)
                else:
                    start_time = time.time()
                    try:
                        retval = self.tb.create(
                            self.topology_yaml,
                            args.additional,
                            args.overwrite,
                            self.run_remotely,
                            args.branch,
                            False,
                            args.different_image_type,
                            args.exclude_vmanage,
                            args.include_hdp,
                            args.include_vs3,
                            args.include_sec_vb23,
                            args.include_vs4,
                            args.include_scaling_vmanage,
                            args.include_vs20,
                            args.qcow2,
                            args.include_scaling_vmanage6,
                            args.include_tlocExt_gre,
                            args.prefer_local_images,
                            args.force_download_branch_images,
                            force_topology_image_vms,
                            args.default_vmanage_volume,
                            args.default_vcontainer_volume,
                            args.no_network_takedown,
                            self.vedge_image_version,
                            args.vedge_build,
                            args.cedge_build,
                            args.cedge_branch,
                            args.dynamic_interface_mapping,
                            self.get_dut_hosts(sanity_check=False),
                            args.dut_lux,
                        )
                        self.summary.set_create_testbed_result('pass')
                    except KeyboardInterrupt:
                        self.summary.set_create_testbed_result('aborted')
                        self.summary.set_create_testbed_text("Received keyboard interrupt")
                    except Exception as err:
                        self.summary.set_create_testbed_result('fail')
                        self.summary.set_create_testbed_text(str(err))
                        self.send_status_to_github_endpoint('failure')
                        self.send_comment_to_github_endpoint('failed to create testbed')
                        self.tb.pause_scheduler(err, True)
                        self.tb.send_pause_email(err, self.recipient)
                        raise
                    finally:
                        duration = int(time.time() - start_time)
                        self.summary.set_create_testbed_time(duration)
            else:
                start_time = time.time()
                try:
                    self.tb.get_ultimate(self.var_dict)
                    retval = self.tb.create(
                        self.topology_yaml,
                        args.additional,
                        args.overwrite,
                        None,
                        args.branch,
                        False,
                        args.different_image_type,
                        args.exclude_vmanage,
                        args.include_hdp,
                        args.include_vs3,
                        args.include_sec_vb23,
                        args.include_vs4,
                        args.include_scaling_vmanage,
                        args.include_vs20,
                        args.qcow2,
                        args.include_scaling_vmanage6,
                        args.include_tlocExt_gre,
                        args.prefer_local_images,
                        args.force_download_branch_images,
                        force_topology_image_vms,
                        args.default_vmanage_volume,
                        args.default_vcontainer_volume,
                        args.no_network_takedown,
                        self.vedge_image_version,
                        args.vedge_build,
                        args.cedge_build,
                        args.cedge_branch,
                        args.dynamic_interface_mapping,
                        self.get_dut_hosts(sanity_check=False),
                        args.dut_lux,
                        args.cedge_cleanup,
                    )
                    self.summary.set_create_testbed_result('pass')
                except KeyboardInterrupt:
                    self.summary.set_create_testbed_result('aborted')
                    self.summary.set_create_testbed_text("Received keyboard interrupt")
                except Exception as err:
                    self.summary.set_create_testbed_result('fail')
                    self.send_status_to_github_endpoint('failure')
                    self.send_comment_to_github_endpoint('failed to create testbed')
                    self.tb.pause_scheduler(err, True)
                    self.tb.send_pause_email(err, self.recipient)
                    raise
                finally:
                    duration = int(time.time() - start_time)
                    self.summary.set_create_testbed_time(duration)

            self.logger.info('Time taken to create testbed: %s', datetime.timedelta(seconds=duration))
            #If testbed creation fails then return False
            if retval != 0:
                self.store_results('Error: Testbed creation failed')
                return False

        if not args.no_lock:
            log_testbed_dir = os.path.join(self.logs_sub_dir, "testbed")
            os.mkdir(log_testbed_dir)
            with open(os.path.join(log_testbed_dir, "config.yaml"), 'w') as config_file:
                config_file.write(yaml.safe_dump(self.tb.config))

        for mch in self.tb.machines():
            machine_log_path = os.path.join(self.logs_sub_dir, mch)
            self.tb.mkpath(machine_log_path)
            tb_expect_log = os.path.join(machine_log_path, '%s-testbed.log' % mch)
            #For each machine pass the tb-log location to testbed
            #This allows us to use the same log file for all shell commands, whether it is through runner or testbed
            #CHANGE: Consider moving this to the next for loop
            self.tb.set_log_file_for_mch(tb_expect_log, mch)

        self.tb.session_with_selinux_permissive = args.selinux_permissive
        self.logger.info('Running testbed with selinux_permissive = %s', args.selinux_permissive)

        ret = 0
        if self.no_certificate:
            self.logger.info('Bringing up the testbed with no certificates installed')
            start_time = time.time()
            ret = -1
            try:
                ret = self.tb.bringup(certs = False)
                self.summary.set_bringup_testbed_result('pass')
            except KeyboardInterrupt:
                self.summary.set_bringup_testbed_result('aborted')
                self.summary.set_bringup_testbed_text("Received keyboard interrupt")
            except Exception as err:
                self.summary.set_bringup_testbed_result('fail')
                self.summary.set_bringup_testbed_text(str(err))
                self.send_status_to_github_endpoint('failure')
                self.send_comment_to_github_endpoint('failed to bringup testbed')
                self.tb.release_lock()
                self.tb.pause_scheduler(err, True)
                self.tb.send_pause_email(err, self.recipient)
                raise
            finally:
                duration = int(time.time() - start_time)
                self.summary.set_bringup_testbed_time(duration)

            self.logger.info('Time taken to bringup testbed: %s', str(datetime.timedelta(seconds=duration)))
            if ret != 0:
                self.tb.pause_scheduler()
                return -99
            self.tb.install_rootca()
        #Get a list of all implicit and explicit tags
        tags = self.get_all_tags(args.tags, args.suite)
        #If the testbed is down, which will be the case if we just created it, then bring it up (unless on a system bed)
        if self.runner_systb is None:
            try:
                status = self.tb.state['status']
            except AttributeError:
                raise TestbedException('testbed "%s" not found' % self.tb.workdir)
            if status == 'down' and not self.no_bringup:
                print(self.no_bringup)
                self.logger.debug('Bringing up the testbed')
                start_time = time.time()
                ret = -1
                print(self.smu)
                try:
                    ret = self.tb.bringup(
                        console_logger=not self.disable_pm_console_logger,
                        date=args.additional,
                        no_parallel_cert=self.no_parallel_cert,
                        bringup_fast=self.bringup_fast,
                        smu=self.smu,
                    )
                    self.summary.set_bringup_testbed_result('pass')
                except KeyboardInterrupt:
                    self.summary.set_bringup_testbed_result('aborted')
                    self.summary.set_bringup_testbed_text("Received keyboard interrupt")
                except Exception as err:
                    self.summary.set_bringup_testbed_result('fail')
                    self.summary.set_bringup_testbed_text(str(err))
                    self.send_status_to_github_endpoint('failure')
                    self.send_comment_to_github_endpoint('failed to bringup testbed')
                    self.tb.release_lock()
                    self.tb.pause_scheduler(err, True)
                    self.tb.send_pause_email(err, self.recipient)
                    raise
                finally:
                    duration = int(time.time() - start_time)
                    self.summary.set_bringup_testbed_time(duration)

                self.logger.info('Time taken to bringup testbed: %s', str(datetime.timedelta(seconds=duration)))
                if ret != 0:
                    self.tb.pause_scheduler()
                    return -99
                #If the valgrind flag was specified then enable valgrind
                if self.valgrind:
                    self.logger.info('Enabling valgrind')
                    ret = self.tb.enable_valgrind()
                    if ret != 0:
                        self.tb.pause_scheduler()
                        return -99
                    #Restart the testbed to start valgrind
                    ret = self.tb.restart()
                    if ret != 0:
                        self.tb.pause_scheduler()
                        return -99
            #If self.restart is true it means -f was specified, we need to clear the cdb and then restart the testbed
            elif self.restart:
                if self.valgrind:
                    self.logger.info('Enabling valgrind')
                    ret = self.tb.enable_valgrind()
                    if ret != 0:
                        self.tb.pause_scheduler()
                        return -99
                ret = self.tb.restart(True)
                if ret != 0:
                    self.tb.pause_scheduler()
                    return -99
                self.restart = False

            if args.upgrade != '':
                self.logger.debug('Upgrading the testbed')
                try:
                    start_time = time.time()
                    res = self.tb.create(
                        None,
                        args.additional,
                        None,
                        None,
                        None,
                        True,
                        args.different_image_type,
                        args.exclude_vmanage,
                        args.include_hdp,
                        args.include_vs3,
                        args.include_sec_vb23,
                        args.include_vs4,
                        args.include_scaling_vmanage,
                        args.include_vs20,
                        args.qcow2,
                        args.include_scaling_vmanage6,
                        args.include_tlocExt_gre,
                        args.prefer_local_images,
                        args.force_download_branch_images,
                        force_topology_image_vms,
                        args.default_vmanage_volume,
                        args.default_vcontainer_volume,
                        args.no_network_takedown,
                        args.cedge_build,
                        args.cedge_branch,
                        args.vedge_build,
                        args.dynamic_interface_mapping,
                        self.get_dut_hosts(sanity_check=False),
                        args.dut_lux,
                    )
                    self.summary.save()
                    self.logger.info('Time taken to create testbed: %s' % str(datetime.timedelta(seconds=(int(time.time()) - int(start_time)))))
                except KeyboardInterrupt:
                    self.summary.set_create_testbed_result('aborted')
                    self.summary.set_create_testbed_text("Received keyboard interrupt")
                except Exception as err:
                    self.summary.set_create_testbed_result('fail')
                    self.summary.set_create_testbed_text(str(err))
                    self.send_status_to_github_endpoint('failure')
                    self.send_comment_to_github_endpoint('failed to create testbed')
                    self.tb.pause_scheduler(err, True)
                    self.tb.send_pause_email(err, self.recipient)
                    raise
                if res != 0:
                    self.logger.debug('Upgrade of the testbed failed')
                    self.tb.pause_scheduler()
                    return -99
        self.logger.info("required to enable nat: %s" % args.enable_nat)
        if args.enable_nat:
            self.tb.configure_nat_on_ubuntu()
        self.logger.info("Save testbed config to logs")
        self.tb.save_config(os.path.join(self.logs_sub_dir, "config.yaml"))

        self.console_connection = args.console_connection
        # Based on the value of the no_traffic_generation flag, create an instance of SpirentSession
        if args.no_traffic_generation or self.args.skip_legacy:
            self.ss = None
        elif args.suite in [
            'nExpress_mtt',
            'nExpress',
            'nExpress_clouddock',
            'vexpress',
            'wlan',
            'mtu',
            'mtu_cedge_rest',
            'syslog_new',
            'cedge_syslog',
            'aaa',
            'vEdgeLifeCycle',
            'LI',
            'aaa_cedge_enhance',
            'syslog_new_rest',
            'aaa_vedge_rest',
            'aaa_cedge_rest',
            'system_stats_verify',
            'cedge_syslog_rest',
        ]:
            self.logger.info('Spirent not required for this suite. Skipping Spirent configuration')
            self.ss = None
        else:
            self.ss = SpirentSession(
                self.tb, self.logger, self.logs_sub_dir, args.reconnect_traffic_generator, self.ssr, self.db_build_id
            )

        # Creation of Ixia session
        if args.no_traffic_generation or not self.tb.is_ixia_configured():
            self.logger.info('Skipping Ixia configuration')
            self.ixias = None
        else:
            ixia_obj = IxiaSession(self.tb.get_ixia_configuration(), self.logger, self.logs_sub_dir)
            if not ixia_obj.is_ixload_client_reachable() or not ixia_obj.is_chassis_reachable():
                self.logger.error('Skipping Ixia configuration as Chassis or ixLoad client is not reachable')
                self.ixias = None
            else:
                self.ixias = ixia_obj

        self.ubuntu = None
        self.ise = None
        self.ad = None
        self.non_dmz = False
        if args.non_dmz:
            self.non_dmz = args.non_dmz

        self.fwconfig = args.firewall_config
        if args.include_ubuntu or args.reboot_ubuntu:
            try:
                self.ubuntu = self.tb.ubuntu_bringup_include(
                    args.suite, args.reboot_ubuntu, args.dynamic_ubuntu, self.non_dmz, qcow_path=args.ubuntu_image
                )
            except Exception as ex:
                self.summary.set_create_testbed_result('fail')
                self.summary.set_create_testbed_text(str(ex))
                self.logger.error('Ubuntu bringup failed')
                self.logger.debug(traceback.format_exc())
                self.store_results('Ubuntu bringup failed')
                raise

        if args.include_ise or args.reboot_ise:
            ise_obj = ISESession(self.logger)
            self.ise = ise_obj

        if args.include_ad or args.reboot_ad:
            ad_obj = ADSession(self.logger)
            self.ad = ad_obj

        self.restapi = False
        if args.restapi_test:
            self.restapi = True
        machines_to_patch = []

        self.cli_template = False
        if args.cli_template_test:
            self.cli_template = True
        machines_to_patch = []

        self.exclude_browser = False
        if args.exclude_browser:
            self.exclude_browser = True

        if args.vmanage_patch is not None:
            if args.remote is None:
                filterdict = self.tb.filters_to_dict(['personality=vmanage'])
                self.tb.patch_vmanage(args.vmanage_patch, filterdict)
                time.sleep(240)
        try:
            if args.csr_patch is not None:
                if args.remote is None:
                    is_csr_cedge =lambda x: self.tb.machine_is_vm(x) and self.tb.is_cedge(x)
                    csr_cedge_list = list(filter(is_csr_cedge, self.tb.machines()))
                    for machine in csr_cedge_list:
                        self.tb.patch_csr(machine, args.csr_patch)
                    machines_to_patch.extend(csr_cedge_list)

            if args.isr_patch is not None:
                if args.remote is None:
                    is_isr_cedge =lambda x: self.tb.machine_is_pm(x) and self.tb.is_cedge(x)
                    isr_cedge_list = list(filter(is_isr_cedge, self.tb.machines()))
                    for machine in isr_cedge_list:
                        self.tb.patch_csr(machine, args.isr_patch)
                    machines_to_patch.extend(isr_cedge_list)

            if len(machines_to_patch) > 0:
                patch_dict = {x:True for x in machines_to_patch}
                res = self.tb.machine_boot_wait(hard_sleep=20, machine_list=patch_dict, max_wait=600)
                if res != 0:
                    self.logger.warn('Issues with machines coming up after patch: {}'.format(machines_to_patch))

            #TODO: Should be removed once issues with upgrade like CSCvh14613 are resolved.
            # ------------------------------------------------------------------------------
            max_cur_serial_id = None
            for machine in machines_to_patch:
                if self.tb.is_cedge(machine):
                    if max_cur_serial_id: max_cur_serial_id += 1
                    else: max_cur_serial_id = self.tb.get_max_serial_id() + 1
                    self.tb.setup_machine(machine, not self.no_certificate, max_cur_serial_id )
            # ------------------------------------------------------------------------------
        except KeyboardInterrupt:
            self.summary.set_create_testbed_result('aborted')
            self.summary.set_create_testbed_text("Received keyboard interrupt")
        except Exception as ex:
            self.summary.set_create_testbed_result('fail')
            self.summary.set_create_testbed_text(str(ex))
            self.logger.error('Failed after upgrading to given image')
            self.logger.error(traceback.format_exc())
            self.send_status_to_github_endpoint('failure')
            self.send_comment_to_github_endpoint('failed after upgrading to given image')
            self.store_results('Patch failed')
            raise

        self.trex = None
        self.trex_stl = None
        self.trex_stf = None
        if 'trex' in pref:
            if args.trex_stateless_generator is not None:
                from sessions import TrexSTLSession
                self.trex = TrexSTLSession(self.tb, self.logger, args.trex_stateless_generator)
                self.trex_stl = self.trex
            if args.trex_stateful_generator is not None:
                from sessions import TrexSTFSession
                self.trex = TrexSTFSession(self.tb, self.logger, args.trex_stateful_generator)
                self.trex_stf = self.trex


        self.pagent = None
        if 'pagent' in pref:
            print('##########Get a pagent here!!!!###########')
            self.pagent = PagentSession(self.tb, self.logger, pref['pagent'])

        # Loop through the list of scripts and run each script
        # Breaking out of this loop will take you to error processing and cleanup
        backed_up = False
        retval = -99
        for script, file_path, yaml_name in self.scripts:
            self.logger.debug('script dir: %s' % Path(file_path).parent)
            self.logger.debug('script name: %s' % script)

            is_sanity = os.path.basename(file_path) == 'test_sanity.ttf'

            if not is_sanity:
                #If we are generating or loading configs then get the configs dir
                if self.generate_configs or self.load_configs:
                    dir_path = os.path.join(os.path.dirname(file_path), 'setup_configs')
                    if yaml_name is None:
                        dir_name = os.path.basename(file_path[: -(len('ttf')) - 1])
                    else:
                        dir_name = '%s_%s' % (os.path.basename(file_path[: -(len('ttf')) - 1]), yaml_name)
                    dir_name = '%s_%s' % (dir_name, self.tb.branch)
                    self.configs_dir_name = os.path.join(dir_path, dir_name)
                    #If we are generating configs then the dest dir might not exist
                    #Go ahead and create it
                    if self.generate_configs:
                        try:
                            os.mkdir(os.path.join(dir_path, dir_name))
                        except OSError:
                            pass
            api = self.instantiate_api(script, yaml_name, file_path)
            if api == -99:
                break
            self.api = api

            # Get the script name and strip the .py from the end of it
            script_name = Path(file_path).stem
            if script_name.startswith("test_"):
                self.db_test_suite = script_name.split('test_', 1)[1]
            elif self.tb.is_cloud_init():
                # testbed is cloud-init, sanity testcases can be skipped
                self.logger.debug("sdwan-init is enabled, skip sanity")
                continue
            else:
                self.db_test_suite = script_name

            ret = 0
            try:
                #Create the ultimate dictionary for the particular script being run
                #This will create pexpect sessions to all the machines
                #It will also create instances of all the classes that we will need for running this particular script
                #This function also checks to see if all the machine versions match, otherwise it prints a warning
                if self.args.skip_legacy:
                    self.crft_export = False
                    self.version_checked = True  # means we already did it
                retval = self.create_ultimate(script, file_path, script_name, no_init=self.args.skip_legacy)
                #If creation of the ultimate dictionary fails then break out of the for loop
                if retval == -99:
                    break
            except Exception:
                #If an exception is thrown print a custom backtrace and then break out of the for loop
                self.logger.info(traceback.format_exc())
                #Set the 'trace' variable to true in order to send the traceback in the stop_email
                trace = True
                self.db_test_suite_result = 'FAIL'
                self.db_core_found = 'Script crash\n'
                self.script_crash = True
                self.summary.set_bringup_testbed_result('fail')
                break

            if not self.version_checked:
                self.initial_version_checks()
                self.init_dt_dash()
                self.configure_machines_etc()
                self.tb.start_monitor(70.0)
                # Set self.version_checked to True so that we dont do this check again
                self.version_checked = True

            # If we are running in prompt mode then return 0
            if retval == 0:
                return 0
            if retval is False:
                ret = 1
                continue
            #Set self.ultimate to the ultimate dictionary returned by the self.create_ultimate function
            self.ultimate = retval
            self.ultimate['ivm'] = not args.exclude_vmanage

            for session in self.session_wrappers():
                self.logger.debug("%s.set_up()", session.__class__.__name__)
                session.set_up()

            try:
                #Back up the core files, from any previous runs, on all the machines
                if not backed_up and not args.quick and self.runner_systb is None:
                    self.logger.info('Moving old core files...')
                    self.backup_core_files(args.remove_core_files)
                    backed_up = True
            except Exception:
                self.logger.info("Failed to collect admin-techs before the tests", exc_info=True)

            # Configure 'system mode insecure' on topology nodes before starting test scripts
            self.tb.configure_system_mode_insecure()
            # Configure 'ip http secure-server' on topology nodes before starting test scripts
            self.tb.configure_http_secure_server()

            # Add ISE xml path
            if args.include_ise or args.reboot_ise:
                reboot = False
                ise_image_local_path = None
                if args.reboot_ise or args.new_testbed:
                    reboot = True
                xml_file = str(Paths().addons('ise-ad/ISE.xml'))
                print('ISE xml_file: %s' % xml_file)
                if not self.ise.checkHandle(self.tb, reboot, self.non_dmz, xml_file, image_path=ise_image_local_path):
                    self.logger.error("Couldn't get ise handle")

            # Add AD xml path
            if args.include_ad or args.reboot_ad:
                reboot = False
                ad_image_local_path = None
                if args.reboot_ad or args.new_testbed:
                    reboot = True
                xml_file = str(Paths().addons('ise-ad/AD.xml'))
                print('AD xml_file: %s' % xml_file)
                if not self.ad.checkHandle(self.tb, reboot, self.non_dmz, xml_file, image_path=ad_image_local_path):
                    self.logger.error("Couldn't get AD handle")

            # Setup the vManage Jacoco code coverage
            if self.vmanage_code_coverage:
                VmanageCodeCoverage(build_id=self.db_build_id).setup()

            # CTC++ code coverage
            if self.coverage_meta_data or self.cflow_coverage:
                self.clean_dat_files()
                self.ctc_coverage = ctc.CtcCollect(self.tb, self.logger)
                self.ctc_coverage.delete_coverage_files()

            # configure auto negotiation on the pms
            confd = self.ultimate["confd"]
            if self.enable_auto_nego_pm:
                for machine in self.tb.machines(types=['pm']):
                    intf_dict = self.tb.interfaces(machine)
                    try:
                        interfaces = [[val['intf'][1], val['vpn']] for val in intf_dict.values()]
                        for iface, vpn in interfaces:
                            result_auto_nego = confd.config_vpn_interface_auto_neg(
                                machine, vpn, iface, remove=False, begin=True, commit=True
                            )
                            if result_auto_nego[0]:
                                self.logger.info('Enabled auto negotiation successfully{}: {}'.format(machine, iface))
                            else:
                                self.logger.warning(
                                    'Failed to enable auto negotiation {}: {}: {}'.format(
                                        machine, iface, result_auto_nego[1]
                                    )
                                )
                    except IndexError:
                        self.logger.warning('Failed to enable auto negotiation {}: '.format(machine))

                    # disabling default gateway
                    result_default_gateway = confd.config_track_default_gateway(
                        machine, remove=True, begin=True, commit=True, device=None
                    )
                    if result_default_gateway[0]:
                        self.logger.info(
                            'Disabled default gateway successfully {}'.format(
                                machine,
                            )
                        )
                    else:
                        self.logger.warning(
                            'Failed to disable default gateway {} : {}'.format(machine, result_default_gateway[1])
                        )
            if not self.no_crft_export:
                # Find cEdge DUTs
                try:
                    cedge_duts = list(
                        set(
                            (
                                m
                                for m in self.tb.machines()
                                if self.tb.is_cedge(m) and self.dtdash_dict['nodes'][m]['dut']
                            )
                        )
                    )
                except Exception as ex:
                    if hasattr(self, 'dtdash_dict'):
                        self.logger.error("[CRFT] Couldn't determine cEdge DUTs: %s", ex)
                    cedge_duts = []

                crft_manager = crft_export_lib.CrftManager(
                    self.tb,
                    self.ultimate["confd"],
                    self.logs_sub_dir,
                    self.db_build_id,
                    self.db_test_suite,
                    cedge_duts,
                    self.message,
                )
                # Enable 'service internal' mode on DUT cEdges and on-reload CRFT collection
                try:
                    crft_manager.enable_service_internal_mode()
                    crft_manager.enable_crft_collection_on_reload()
                except Exception as ex:
                    self.logger.error("[CRFT] %s", ex)
                # Delete old CRFT files, clear CRFT counters and collect baseline counters
                try:
                    crft_manager.delete_crft_files()
                    crft_manager.clear_crft_counters()
                    crft_manager.collect_crft_counters(baseline=True)
                except Exception as ex:
                    self.logger.error("[CRFT] %s", ex)

            # Run the script
            try:
                pname = file_path.rpartition('/')[-1][:-4]
                with self.profiler.run(pname):
                    # If the suite being run is sanity then dont pass any tags
                    # The second argument that is passed is the pattern we look for to figure out which functions are test cases
                    retval = self.run_script(file_path)
            except Exception:
                # If an exception is thrown print a custom backtrace and then break out of the for loop
                self.logger.info(traceback.format_exc())
                # Set the 'trace' variable to true in order to send the traceback in the stop_email
                trace = True
                self.db_test_suite_result = 'FAIL'
                self.db_core_found = 'Script crash\n'
                self.script_crash = True
                break
            finally:
                if not is_sanity and args.quick is False and self.runner_systb is None:
                    #Check to make all the required processes are still running on every machine
                    try:
                        process_retval = self.check_processes(script)
                    except Exception:
                        process_retval = 0
                        #If an exception is thrown print a custom backtrace and then break out of the for loop
                        self.logger.info(traceback.format_exc())
                        #Set the 'trace' variable to true in order to send the traceback in the stop_email
                        trace = True
                        self.db_test_suite_result = 'FAIL'
                        self.db_core_found = 'Script crash\n'
                        self.script_crash = True
                        break
                    finally:
                        #If any of the processes has died restart the testbed
                        if process_retval != 0:
                            self.restart = True
                            self.login_if_restart = True
                else:
                    process_retval = 0
            #If sanity was specified as a tag then break out of the for loop as we have run through sanity
            if 'sanity' in args.tags:
                break
            #If there were failures in the script then set 'ret' to 1
            if retval != 0 or process_retval != 0:
                ret = 1
                #If the script being run was sanity or if the stopatfail flag was specified then break out of the for loop
                if is_sanity or retval == -1:
                    break

        self.final_version_checks()

        # Stop monitoring Process and it's threads
        self.tb.stop_monitor(False)

        # Get the vManage code coverage
        if self.vmanage_code_coverage:
            VmanageCodeCoverage(build_id=self.db_build_id).teardown()

        # Selinux denial checks on cEdge devices
        if self.selinux:
            self.selinux_denial_check()

        if 'TB_ORG_NAME' in os.environ:
            self.logger.info('Org name is set to %s, we need to unreserve it' % os.environ.get('TB_ORG_NAME'))
            unreserve_org_name(self.logger)

        # We are done running tests, now its time report the errors and collect all the logs
        try:
            if self.core_found:
                self.db_test_suite_result = 'FAIL'
            if self.db_test_suite_result == 'PASS':
                self.send_status_to_github_endpoint('success')
                self.send_comment_to_github_endpoint('passed')
            else:
                self.send_status_to_github_endpoint('failure')
                self.send_comment_to_github_endpoint('failed to pass')
            if self.valgrind:
                self.tb.disable_valgrind()
                for mch in self.tb.machines():
                    self.ultimate['confd'].reboot_node(mch, 90, True)

            # As long as we did not break out of the for loop because of an ultimate dictionary creation failure then get logs from all the machines
            # Dont fetch the logs if the quick flag is specified
            if retval != -99:
                if not self.no_crft_export:
                    # Collect CRFT counters after the tests are finished and export CRFT files
                    try:
                        crft_manager.collect_crft_counters()
                        crft_manager.export_crft_files()
                    except Exception as ex:
                        self.logger.error("[CRFT] %s", ex)
                else:
                    self.logger.info("[CRFT] CRFT data won't be collected due to '-no_crft_export' argument")
                if args.quick is False:
                    self.get_var_logs()
                if self.crft:
                    self.collect_crft()
            else:
                self.logger.error("[CRFT] retval is %s. CRFT data won't be collected", retval)

            # Export information about Certificates from DUT devices
            self.log_cert_on_devices()
            # If there were any warnings print them
            if len(self.warnings_list) > 0:
                self.logger.warning(self.print_line(char='='))
                self.logger.warning(' ' * 37 + 'WARNINGS')
                self.logger.warning(self.print_line(char='='))
            # Print all the warnings for the entire run
            for item in self.warnings_list:
                self.logger.warning(item)
            #Print a header for the errors
            if len(self.errors_list) > 0:
                self.logger.error(self.print_line())
                self.logger.error(' ' * 37 + 'ERRORS')
                self.logger.error(self.print_line())
            #Print all the errors for the entire run
            for item in self.errors_list:
                self.logger.error(item)
            if len(self.errors_list) > 0:
                self.logger.error(self.print_line())
            #Uploads the test suite report to Cerebro if -ctc argument passed as part of runner command
            if self.coverage_meta_data:
                # find at least one cEdge instrumented machine
                cedge_instrumented = False
                for machine in self.tb.machines():
                    if self.tb.is_cedge(machine):
                        if self.check_instrumented_cedge_image(machine):
                            cedge_instrumented = True
                            self.logger.info("Found cEdge Instrumented image.")
                            break
                if cedge_instrumented:
                    self.upload_to_cerebro()
                else:
                    self.logger.info("No cEdge Instrumented image found.")

                # CTC++ code coverage for vEdge
                self.ctc_coverage.restart_vedge_vms()
                self.ctc_coverage.collect_mon_files_to_testbed()
                self.ctc_report = ctc.GenerateReport(self.tb, self.logger, self.db_build_id)
                self.ctc_report.generate_reports()
                self.ctc_upload = ctc.UploadToCerebro(
                    self.tb, self.logger, self.db_build_id, self.args_string, self.suite
                )
                self.ctc_upload.send_html_to_cerebro()

            if self.ssr:
                self.summary.dump_xml(self.summary.get_pyats_summary(), 'ResultsSummary.xml')
                self.summary.dump_xml(self.summary.get_pyats_details(self.suite_name), 'ResultsDetails.xml')
            self.test_stats = self.print_test_stats()
            self.summary.add_testbed_info(self.tb.get_assigned_images(), self.get_dut_hosts(sanity_check=False))
            # Write the xml summary to a file
            self.summary.save()

            # CSCwf26272 append sdwan-init: true if testbed is sdwan-init mode in end of exec
            if self.tb.is_cloud_init():
                if isinstance(self.message, str):
                    self.message += " sdwan-init: true"
                try:
                    with self.get_db_client() as db_handle:
                        if self.db_build_id:
                            db_handle.update_comment_to_db(self.db_build_id, self.message)
                        else:
                            self.logger.warning("db_build_id is null")
                except Exception:
                    self.logger.warning("Failed to update sdwan-init flag to db.", exc_info=True)

            #If we are not running in prompt mode and the no_email tag is not specified, send a results email
            if not self.prompt and self.email:
                self.store_results('stop', trace, tags, args.message)

            # Final check if all TCs were added to regressDB and their status is updated
            self._check_rdb_tcs()

            # Close all log files for the expect sessions, we might not actually need this any more since this is being done in the __del__() func
            self.close_expect_logs()
        except Exception:
            # If an exception was thrown, handle it and print a custom backtrace
            self.logger.info(traceback.format_exc())

        # If the stopatfail flag was specified and there was a failure and we are running on a server, then pause the scheduler
        if self.first_fail and retval != 0 and self.server:
            msg = 'Failure on %s, -x specified' % self.tb.workdir
            subprocess.call('scheduler pause True -t \"%s\" -e cronjob_bot@viptela.com' %msg, shell = True)
        else:
            if args.update_stable_link and ret == 0:
                self.update_stable_link()

            # If the generate_configs flag was specified then clear the cdb and restart the testbed
            if self.generate_configs:
                retval = self.tb.restart(True)
                if retval != 0:
                    self.tb.pause_scheduler()
                    return -99

            # If the cleanup tag was specified, take down the testbed
            if args.cleanup:
                for machine in self.tb.machines():
                    if args.software_maintenance_upgrade and machine == "pm5":
                        self.tb.deactivate_smu(machine, self.smu)
                        self.tb.remove_smu(machine, self.smu)
                if args.cleanup_start_dhcp is not None:
                    if args.cleanup_start_dhcp:
                        if args.dhcp_server_intf is None:
                            raise ValueError("DHCP server interface required for enabling DHCP server not specified.")
                        else:
                            self.enable_disable_dhcp_server(True, args.dhcp_server_intf)
                elif args.cleanup_stop_dhcp is not None:
                    if args.cleanup_stop_dhcp:
                        if args.dhcp_server_intf is None:
                            raise ValueError("DHCP server interface required for disabling DHCP server not specified.")
                        else:
                            self.enable_disable_dhcp_server(False, args.dhcp_server_intf)

                self.tb.stop_monitor(False)
                start_time = time.time()
                try:
                    self.tb.takedown()
                    self.summary.set_takedown_testbed_result('pass')
                except KeyboardInterrupt:
                    self.summary.set_takedown_testbed_result('aborted')
                    self.summary.set_takedown_testbed_text("Received keyboard interrupt")
                except Exception as ex:
                    self.summary.set_takedown_testbed_result('fail')
                    self.summary.set_takedown_testbed_text(str(ex))
                finally:
                    duration = int(time.time() - start_time)
                    self.summary.set_takedown_testbed_time(duration)
                    self.logger.info('Time taken to takedown testbed: %s', datetime.timedelta(seconds=duration))
        return ret

    def _check_rdb_tcs(self):
        """
        Check if all TCs were added to regressDB and their status is updated.
        Check uses local info stored in self._tcs_summary dictionary
        TC name that had exception during updates is collected in self._tcs_update_errors set.

        This prevents following issues when TCs were not added to regressDB or not updated after being properly added,
        due to:
            - some issues in communication to regressDB during suite execution (e.g. lock timeout)
            - initial communication error - regressDB ID and summary is generated at the end of run - we need to update TCs
            - other regress db intermittent issues


        """
        if self.db_write and self.db_build_id:
            try:
                with self.get_db_client() as db_handle:
                    # Loop 1 - add missing TCs
                    for tc_name, update in self._tcs_summary.items():
                        if not db_handle.tc_exists(tc_name, self.db_build_id):
                            self.logger.info("Updating missing TC to DB: {}".format(tc_name))
                            db_handle.push_test_to_db(*update)

                    # Loop 2 - update state of TCs that experienced Exception during any of possible updates
                    for tc_name in self._tcs_update_errors:
                        self.logger.info("Updating TC {} results to DB due to previous exception".format(tc_name))
                        db_handle.update_tc_state(*self._tcs_summary[tc_name])

            except sqldb.SqldbConnectionError as e:
                self.logger.error("Error while connecting to DB duirng checking / updating TC.\n{}".format(e))
            except Exception as e:
                self.logger.error("Error while checking / updating TC: {}: {}".format(tc_name, e))

    def close_expect_logs(self):
        for f in self.expect_logs:
            f.close()
        self.expect_logs = []

    def run_local_tests(self, file_path, patch, suite, args_list, vmanage_patch_old):
        """
        Submits the job to the testbed with a local patch file
        """
        res = self.check_suite_support(self.tb_hostname, suite)
        if res != 0:
            return res
        try:
            # Find '-b' tag
            index = args_list.index('-b')
            # Get string after '-b' tag
            branch = args_list[index + 1]
        except ValueError:
            branch = None
        # Check to see if branch is supported on local machine
        res = self.check_branch_support(self.tb_hostname, branch)
        if res != 0:
            return res
        images_loc = file_path
        images_loc = os.path.abspath(images_loc)
        # Remove unnecessary args before adding task to scheduler
        try:
            index = args_list.index('-fp')
        except ValueError:
            index = args_list.index('--file_path')
        # Remove '--fp/file_path' string, and supplied path
        args_list.pop(index)
        args_list.pop(index)
        try:
            index = args_list.index('-loc')
            # Remove -loc argument
            args_list.pop(index)
        except ValueError:
            print("File path and/or local args were not supplied properly")
            return 1
        for index in range(len(args_list)):
            arg = args_list[index]
            if type(arg) == str:
                if ' ' in arg:
                    # Make sure the quotes are escaped in the string when supplied to scheduler
                    args_list[index] = "'%s'" % args_list[index]
        tb_name = pwd.getpwuid(os.getuid())[0]
        args_str = ' '.join(args_list)
        if 'email' in pref:
            recipient = pref['email']
        else:
            recipient = '%s@viptela.com' % tb_name
        # Create zip file
        timestamp = time.strftime('%Y-%m-%d_%H-%M-%S', time.gmtime())
        images_zip = '%s-%s.zip' % (tb_name, timestamp)
        images_dir = file_path.rstrip('/')
        dir_loc = os.path.dirname(images_dir)
        images_dir = os.path.basename(images_dir)
        if len(dir_loc) > 0:
            os.chdir(dir_loc)
        if not os.path.isdir(images_dir):
            if images_dir[-4:] == '.zip':
                images_dir_temp = images_zip[:-4]
                os.mkdir(images_dir_temp)
                if patch is not None:
                    patch_file = os.path.join(images_dir_temp, 'patch.zip')
                    shutil.copy(images_dir, patch_file)
                    if vmanage_patch_old:
                        patch_file = os.path.join(images_dir_temp, 'patch_vmanage.zip')
                        shutil.copy(vmanage_patch_old, patch_file)
                else:
                    if vmanage_patch_old:
                        patch_file = os.path.join(images_dir_temp, 'patch_vmanage.zip')
                        shutil.copy(vmanage_patch_old, patch_file)
                    else:
                        shutil.copy(images_dir, images_dir_temp)
                images_dir = images_dir_temp
        print("zip -r %s %s" % (images_zip, images_dir))
        res = subprocess.call(['zip', '-r', images_zip, images_dir])
        shutil.rmtree(images_dir)
        os.rename(images_zip, str(Paths().images('')) + images_zip)
        if res != 0:
            print("Could not create a zip file from the images directory")
            return 1
        try:
            vtest_path = str(Paths().vtest())
            subprocess.call(
                f"scheduler add_task \"cd {vtest_path}/tests; find ./ -name '*.pyc' -delete; rm {vtest_path}/addons/misc.pyc;"
                f" git stash; runner {args_str} -n {tb_name} -o -R {images_zip} -U {recipient} -v -c\" -p 3 -e cronjob_bot@viptela.com",
                shell=True,
            )
        except OSError as e:
            print("Error with adding task to scheduler")
            print(e)
            return 1
        return 0

    def run_remote_tests(self, remote_args, patch, suite, args_list, vmanage_patch_old, vmanage_patch=None):
        """
        Submits the job to a remote server rather than running it on the local machine
        """
        #Get the remote machine where we need to run
        remote_machine = remote_args[0]
        res = self.check_suite_support(remote_machine, suite)
        if res != 0:
            return res

        #Get the branch and check if the branch is supported in the testbed
        try:
            index = args_list.index('-b')
            branch = args_list[index + 1]
        except ValueError:
            branch = None

        res = self.check_branch_support(remote_machine, branch)
        if res != 0:
            return res
        #Get the location of the images to use
        images_loc = remote_args[1]
        if images_loc == 'fetch':
            #If the images_loc == 'fetch' then set images_loc to None. This will tell the remote testbed to pull the latest images
            images_loc = None
        else:
            #Else get the absolute path to the images_loc
            images_loc = os.path.abspath(images_loc)
        #Ignore for now
        config = None
        #Get the index of the -r/--remote tag from the list of args
        try:
            index = args_list.index('-r')
        except ValueError:
            index = args_list.index('--remote')
        #Remove the tag and all of its args from the list
        args_list.pop(index)
        args_list.pop(index)
        args_list.pop(index)
        #If any of the arguments are strings which have whitespaces in them we have to make sure the string is enclosed in quotes.
        for index in range(len(args_list)):
            arg = args_list[index]
            if type(arg) == str:
                if ' ' in arg:
                    #We have to make sure the quotes are escaped in the string went to the remote server
                    args_list[index] = "'%s'" % args_list[index]
        #Get the values for the yaml_file, different_image_type and branch, if specified, from the args list
        #We need these values for creating a remote testbed
        try:
            index = args_list.index('-y')
            remote_yaml = args_list[index + 1]
        except ValueError:
            remote_yaml = None
        try:
            index = args_list.index('-df')
            diff_image_type = args_list[index + 1]
        except ValueError:
            diff_image_type = None
        #Convert the list of args to a string
        args_str = ' '.join(args_list)
        #Get the hostname of the local machine
        #We will use this as the name for the testbed we create on the server
        tb_name = pwd.getpwuid(os.getuid())[0]
        #Use the name we just got to create an instance of vmware(testbed)
        tb = HyperVisor(tb_name)
        tb.clear_handlers()
        #Call the tb.create_remote function which will create a zip containing all the files we need and then scp them to the server
        retval = tb.create_remote(remote_machine, images_loc, config, patch, True, branch, diff_image_type, remote_yaml, vmanage_patch_old)
        #If the return value was not a string then something failed
        if type(retval) != list:
            return 1
        #Else retval is the name of the zip file that was just copied to the server, this name of this file is hostname_timestamp.zip
        else:
            ssh_session, images_zip = retval
        #If the user name for the remote server is not given (in which case use tester) or a dns name is specified instead of the ip address then resolve it
        remote_machine = misc.resolve_remote_machine(remote_machine)
        #If the email parameter is specified in the preference file, use that, else use hostname@viptela.com
        if 'email' in pref:
            recipient = pref['email']
        else:
            recipient = '%s@viptela.com' % tb_name
        #Create the command to submit to the server
        #This 'scheduler add_task' will add the command to the scheduler's queue
        #When the command is executed it will first stash all the vtest changes and then run 'runner' command
        res = 0
        vtest_path = str(Paths().vtest())
        if self.vmanage_patch is not None:
            destdir = str(Paths().images(''))
            patchfilename = os.path.split(self.vmanage_patch)[1]
            destfile = os.path.join(destdir, patchfilename)
            sftp_session = ssh_session.open_sftp()
            try:
                sftp_session.put(self.vmanage_patch, destfile)
                self.logger.info('vmanage .war patch uploaded to remote testbed')
                _, _, stderr = ssh_session.exec_command(
                    f"scheduler add_task \"cd {vtest_path}/tests/; find ./ -name '*.pyc' -delete; rm {vtest_path}/addons/misc.pyc;"
                    f" git stash; runner {args_str} -n {tb_name} -o -U {recipient} -vmp {destfile} -v -c\" -p 3 -e cronjob_bot@viptela.com"
                )
                res = tb.print_ssh_cmd_err(stderr)
            except Exception as e:
                self.logger.error('Unable to upload file to testbed')
                raise e
        elif self.csr_patch is not None:
            destdir = str(Paths().images(''))
            patchfilename = os.path.split(self.csr_patch)[1]
            destfile = os.path.join(destdir, patchfilename)
            sftp_session = ssh_session.open_sftp()
            try:
                sftp_session.put(self.csr_patch, destfile)
                self.logger.info('CSR *.bin uploaded to remote testbed')
                _, _, stderr = ssh_session.exec_command(
                    f"scheduler add_task \"cd {vtest_path}/tests/; find ./ -name '*.pyc' -delete; rm {vtest_path}/addons/misc.pyc;"
                    f" git stash; runner {args_str} -n {tb_name} -o -U {recipient} -csrp {destfile} -v -c\" -p 3 -e cronjob_bot@viptela.com"
                )
                res = tb.print_ssh_cmd_err(stderr)
            except Exception as e:
                self.logger.error('Unable to upload file to testbed')
                raise e
        elif self.isr_patch is not None:
            destdir = str(Paths().images(''))
            patchfilename = os.path.split(self.isr_patch)[1]
            destfile = os.path.join(destdir, patchfilename)
            sftp_session = ssh_session.open_sftp()
            try:
                sftp_session.put(self.isr_patch, destfile)
                self.logger.info('ISR *.bin uploaded to remote testbed')
                _, _, stderr = ssh_session.exec_command(
                    f"scheduler add_task \"cd {vtest_path}/tests/; find ./ -name '*.pyc' -delete; rm {vtest_path}/addons/misc.pyc;"
                    f" git stash; runner {args_str} -n {tb_name} -o -U {recipient} -isrp {destfile} -v -c\" -p 3 -e cronjob_bot@viptela.com"
                )
                res = tb.print_ssh_cmd_err(stderr)
            except Exception as e:
                self.logger.error('Unable to upload file to testbed')
                raise e
        else:
            _, _, stderr = ssh_session.exec_command(
                f"scheduler add_task \"cd {vtest_path}/tests/; find ./ -name '*.pyc' -delete; rm {vtest_path}/addons/misc.pyc;"
                f" git stash; runner {args_str} -n {tb_name} -o -R {images_zip} -U {recipient} -v -c\" -p 3 -e cronjob_bot@viptela.com"
            )
            res = tb.print_ssh_cmd_err(stderr)
        ssh_session.close()
        if res == 0:
            self.logger.info('Successfully submitted job to server')
        else:
            self.logger.error('Could not schedule job on server')
        return res

    def create_loggers(self, debug, remote, logs_sub_dir=None):
        """
        Get the logger and attach handlers to it
        """
        #Set the log level depending on the debug level, we are not really using this
        if debug:
            devel_lvl = logging.DEBUG
        else:
            devel_lvl = logging.INFO
        #Get the current timestamp, we will use this to stamp our logs
        self.timestamp = time.strftime('%Y-%m-%d-%H:%M:%S', time.gmtime(self.start))
        if logs_sub_dir is not None:
            self.logs_sub_dir = os.path.join(self.logs_dir, logs_sub_dir)
        else:
            #If the job was submitted by a remote guy then use the name of the zip file, that we received through scp, as the name for the logs dir
            if self.run_remotely is not None:
                self.logs_sub_dir = os.path.join(self.logs_dir, '%s' % self.run_remotely.rstrip('.zip'))
            #Else use the timestamp
            else:
                self.logs_sub_dir = os.path.join(self.logs_dir, '%s' % self.timestamp)
        set_log_root(self.logs_sub_dir)
        #If this job is not being submitted to a server, create the logs subdir
        if remote is None:
            try:
                os.mkdir(self.logs_sub_dir)
            except OSError as err:
                #Do not raise if folder already exists
                if err.errno == 17:
                    pass
            # softlink current_log
            current_log = os.path.join(self.logs_dir, 'current_log')
            subprocess.call('rm %s' % (current_log), shell=True)
            subprocess.call('ln -s %s %s' % (self.logs_sub_dir, current_log), shell=True)
            with open(os.path.join(self.logs_dir, 'latest_log'),'w') as f:
                f.write(os.path.basename(self.logs_sub_dir))

        # Get the logger
        self.logger = logging.getLogger('tests_logger')
        # Remove any of the existing handlers from the logger
        # for handler in self.logger.handlers:
        #    self.logger.removeHandler(handler)
        #Set the level of the logger itself
        self.logger.setLevel(logging.DEBUG)
        # self.log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.log_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
        )
        logging.Formatter.converter = time.gmtime
        #If this job is not being submitted to a server
        logs = {}
        if remote is None:
            for lvl in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                logs[lvl] = {}
                logs[lvl]["log_file"] = os.path.join(self.logs_sub_dir, "{}.log".format(lvl.lower()))
                logs[lvl]["log_filehandler"] = logging.FileHandler(logs[lvl]["log_file"], 'w')
                logs[lvl]["log_filehandler"].setFormatter(self.log_formatter)
                logs[lvl]["log_filehandler"].setLevel(getattr(logging, lvl))
                self.logger.addHandler(logs[lvl]["log_filehandler"])

            os.symlink("info.log", os.path.join(self.logs_sub_dir, "run.log"))
            os.symlink("debug.log", os.path.join(self.logs_sub_dir, "tester.log"))

        stream = vtest_logging.OppStreamHandler(sys.stdout)
        stream_err = logging.StreamHandler()
        stream.setFormatter(self.log_formatter)
        stream_err.setFormatter(self.log_formatter)
        #Set the logging levels for the handler
        stream.setLevel(devel_lvl)
        stream.setMaxLevel(logging.WARN)
        stream_err.setLevel(logging.ERROR)
        #Add the handler to the logger
        self.logger.addHandler(stream)
        self.logger.addHandler(stream_err)
        self.logger.propagate = 0
        #If the flag for getting the nc_client output is specified set the ncclient logger level to debug and a file handler to it
        if self.ncclient:
            ncclient_output_file = os.path.join(self.logs_sub_dir, 'nc_netconf.log')
            ncclient = logging.getLogger('ncclient')
            ncclient.setLevel(logging.DEBUG)
            ncclient.propagate = 0
            handler = logging.FileHandler(ncclient_output_file, 'w')
            handler.setFormatter(self.log_formatter)
            ncclient.addHandler(handler)
        VLogging.register(self.logs_sub_dir)
        VLogging('runner').set_logger(self.logger)
        self.libs_logger = LibsLoggerController.default(VLogging.path)
        self.libs_logger.start()

    def stop_loggers(self):
        self.libs_logger.stop()

    def get_protocol_yaml(self, protocol):
        self.logger.warning("**************************************************")
        self.logger.warning("*                                                *")
        self.logger.warning("* Defining protocol in Runner.get_protocol_yaml  *")
        self.logger.warning("*     is deprecated.                             *")
        self.logger.warning("*                                                *")
        self.logger.warning("* Please add protocol to your TTF file, example: *")
        self.logger.warning("*     modules   = ['omp', 'cExpress']            *")
        self.logger.warning("*     protocol  = 'omp'                          *")
        self.logger.warning("*     dut_hosts = ['vm5', 'pm5']                 *")
        self.logger.warning("*     topology  = 'viptela_vulcan_kvm'           *")
        self.logger.warning("*                                                *")
        self.logger.warning("**************************************************")
        protocol_yaml = ''
        if True: # Preserve spacing
            if protocol == 'vmanage_sdwan' and os.uname()[0] == 'Darwin':
                protocol_yaml = 'reduced_vmanage'
            elif self.include_scaling_vmanage6:
                protocol_yaml = 'vmanageScaling_dual_tb69'
            elif self.include_scaling_vmanage and self.include_sec_vb23:
                if protocol in ['vdaemon']:
                    protocol_yaml = protocol
                    if self.reverse_proxy:
                        protocol_yaml = '%s_proxy'%(protocol)
                else:
                    protocol_yaml = 'vmanage_scaling_certs'
            elif self.include_sec_vb23 and protocol not in [
                'vdaemon',
                'ipsec',
                'vdaemonv4v6',
                'affinity',
                'proxy',
                'mttproxy',
            ]:
                protocol_yaml = 'certs'
            elif protocol in [
                'apps_performance',
                'apps_performance_206',
                'rbac_device_variable_P0',
                'rbac_comanagement_ph3_P0',
                'sdra_resource_manager_P0',
            ]:
                if self.include_scaling_vmanage:
                    protocol_yaml = 'vmanageScaling_dual'
                else:
                    protocol_yaml = 'omp_dual'
            elif protocol in [
                'esim',
                'isr1k-cg',
                'cEdgeElixirwifi6',
                'configuration_groups_wireless_switchport_svi',
                'configuration_groups_cEdgeT1E1',
                'configuration_groups_optional_rows_DT',
                'cEdgeSerial',
                'cEdgeISR1Kwifi',
                'cEdgeFlexL2L3',
                'cEdgePBR',
                'cEdgeSwitzer',
                'cEdgeSwitzerManhattan',
                'cEdgeDot1x',
                'cEdgeT3E3',
                'cEdgeT1E1',
                'cEdgeAsync',
                'cEdgeNBAR',
                'NBAR_DPI_Policy',
                'dhcpv4v6',
                'forwarding',
                'device_policy',
                'omp',
                'omp_block1',
                'omp_block2',
                'omp_block3a',
                'omp_block3b',
                'omp_block4',
                'omp_cEdge_rest',
                'omp_vEdge_rest',
                'mtu',
                'mtu_vedge_rest',
                'mtu_cedge_rest',
                'tcpMss',
                'ddos',
                'dot1x',
                'qos',
                'qos_cedge',
                'qos_cedge_subif',
                'qos_cedge_v4v6',
                'qosv4v6_cedge_subif',
                'qos_x86',
                'qos_cedge_vmanage',
                'qos_cedge_vmanage_cli',
                'qos_cedge_aut',
                'nwpi_cypress',
                'nwpi',
                'nwpi_p3',
                'nat',
                'vedge_nat_alg',
                'cflowd',
                'vmanage_sdwan',
                'routeLeakcEdge',
                'routeLeakcEdge_Redistribution',
                'routeLeakcEdge_rest',
                'routeLeakOmpAdVrrp_new',
                'cert_mgmt',
                'vman_omp_template',
                'vman_omp_cfg_templ',
                'vman_ztp_omp_cfg_templ',
                'vs_gui_policy',
                'MibParitycEdge',
                'dpi',
                'vEdgeNitro',
                'cEdge_Nbar',
                'snmp',
                'MIB_parity_appcflowd',
                'SNMPv3_AES256',
                'gre_external',
                'gre_external_rest',
                'vplatform',
                'policy',
                'switching',
                'switching_dual',
                'cEdgeSwitching',
                'vman_certs',
                'vman_certs_revamp',
                'wlan',
                'throughput',
                'iptable',
                'upgrade',
                'syslog_new',
                'cedge_syslog',
                'aaa',
                'tcpopt',
                'ztp',
                'standard_ipsec',
                'standard_ipsec_tier1',
                'on_ramp',
                'cEdgeNat',
                'cEdgeNatMapeTloc',
                'cEdgeNat_dual',
                'cEdgeNatPoolDia',
                'nat_bfd_port_preserve',
                'destinationNat',
                'cEdgeNatAlgTFTP',
                'cEdgeNatMultiDia',
                'cEdgeFNF',
                'fwd_arp_and_app',
                'fwd_ipv6',
                'fwd_last_resort',
                'fwd_policy',
                'fwd_policy_2',
                'fwd_policy_rest',
                'fwd_ip_direct_broadcast',
                'fwd_ip_direct_broadcast_rest',
                'fwd_secondary_ip',
                'fwd_secondary_ip_rest',
                'fwd_low_bandwidth',
                'vman_omp_cfg_templ_robot',
                'fwd_ipv6_rest',
                'vman_ztp_omp_cfg_templ_robot',
                'vman_omp_template_robot',
                'vedge_cli_templates',
                'cExpress',
                'secret_type',
                'alarms_isr',
                'teacat_CSCvy50092',
                'tea_CSCwa37370',
                'ft_CSCvz25285_CSCvy95518',
                'ft_CSCvy95518',
                'teacat_CSCwc85315',
                'dr',
                'cExpress_mini',
                'Logging_cli_template',
                'cli_aaa_snmp_hardening',
                'cEdgedevicepolicy',
                'nping_traceroute',
                'cEdgePolicy',
                'cEdgePolicy_teacat',
                'ACLimplicitexplicit',
                'cEdgePolicy_serv_ipv4_trans_ipv6',
                'cEdgePolicy_serv_ipv6_trans_ipv4',
                'cEdgePolicy_serv_ipv6_trans_ipv6',
                'cEdgeBFD',
                'scale_vrf',
                'PPPoE_rar_sdwan',
                'pnp',
                'vedge_ztp',
                'vedge_ztp_EnforceUpgrade',
                'rip_service_side',
                'vedge_packet_tracer',
                'vedge_splitadmin',
                'vedge_cliauthorization_ut',
                'pnp_modechange',
                'teacat_vedge',
                'cedgesnmpv3',
                'F116860_Audit_Capabilities',
                'ogacl',
                'vedge_forwarding_precommit_sanity',
                'vedge_fec_pkt_dup_dev_sanity',
                'vedge_forwarding_dev_sanity',
                'vedge_mtu_dev_sanity',
                'zbfw',
                'zbfw_vmanage',
                'dsl',
                'cEdgePolicycustomApp',
                'cEdgePolicycustomApp_CAT',
                'cEdgePolicyNexthoplooose',
                'fwdPolicyAARdampening',
                'servicesUpgrade',
                'configuration_groups_20_8',
                'configuration_groups_20_9',
                'configuration_groups_cidr_dt',
                'configuration_groups_uc',
                'configuration_groups_uc_dspfarm',
                'configuration_groups_ospf_wan_parcel_DT',
                'configuration_groups_ospfv3_parcel_DT',
                'configuration_groups_localized_policy',
                'configuration_groups_multicast_DT',
                'configuration_groups_device_access_policy_DT',
                'configuration_groups_perfmonitor',
                'configuration_groups_tracker_ipsec_security',
                'configuration_groups_3rd_party_ca',
                'configuration_groups_vpn_qos',
                'configuration_groups_qos',
                'configuration_groups_tags',
                'configuration_groups_custom_workflow',
                'configuration_groups_DIA_tracker',
                'policy_groups_DT',
                'policy_groups_simple_workflow_DT',
                'policy_groups_phase2_DT',
                'template_push_sanity',
                'template_mcast',
                'embargo',
                'embargo_api',
                'per_class_aar',
                'mcast_aar',
                'netconf_notif',
                'cEdgetlocweight',
                'nExpresscEdge',
                'cEdgeTloc',
                'cEdgeUpgrade',
                'umbrella',
                'localized_policy_builder',
                'single_vmanage_view_for_wan_tunnel',
                'amazon_testing',
                'sshsnmp_policy_builder',
                'st_mtt_migration_st_setup_cleanup',
                'st_mtt_migration_mtt_setup_cleanup',
                'fedramp_session_management',
                'eigrp_template',
                'template_ipv6_transport',
                'cEdgeTloc_rest',
                'ds_pcap_speed',
                'ds_speed_cedge',
                'utd',
                'ztp_upgrade',
                'ospfv3_api',
                'cEdgeddos',
                'appfw',
                'appfw_dia',
                'cedgeicmpv6',
                'vrrpv3',
                'hsrp_nat_red',
                'mape',
                'hsrp_flex',
                '178_RIPng',
                '209_sha1_dis_weak',
                'te_app_sdwan_nutella',
                'dhcpv6_relay',
                'zbfwnat',
                've5k_throughput',
                'sdavc',
                'sda',
                'aci',
                'central_ipv6_pol',
                'common_inventory',
                'mtt_common_inventory',
                'LI',
                'cExpressv4v6',
                'cedge_feature_template_validation',
                'vpn_feature_template',
                'selfzone',
                'disaster_recovery',
                'dSetting',
                'globalTemplate',
                'cExpress_temp',
                'cExpress_mini_temp',
                'cedge_precommit',
                'sdwan_ssr_express',
                'cEdge_fwd_low_bandwidth',
                'teacat_basic',
                'teacat_basic_2cedge',
                'cedge_qos_stats_monitor',
                'cedge_fnf_spreading',
                'sudi_otp',
                'appqoe',
                'default_feature_template',
                'vman_security_posture',
                'password_guidelines',
                'vedge_password_policy',
                'cEdge_XE_BFD',
                'cEdge_XE_sla',
                'compactSanity_services1',
                'cedge_ztp',
                '1710_2010_SW_enf_ZTP_upgrade_rs',
                'cedge_speed_pcap',
                'cedge_platform_template_validation',
                'vManage_compact_regression',
                'upgrade_stable',
                'route_leak_vedge',
                'dual_dia_tracker',
                'dia_tracker',
                'cedge_dia_tracker',
                'cedge_ubuntu_dual_stack_DIA_icmp_tracker',
                'ipv4_tracker_v4ov6_tunnel',
                'static_route_tracker',
                'static_route_tracker_scale',
                'template_migration',
                'cEdgeUpgrade_compact',
                'route_leak_vedge_rest',
                'ipsec_pki_import',
                'vrrp_tracking',
                'nutella_xe',
                'vman_dual_ned',
                'cedge_fnf_ipv6',
                'sig_vmanage',
                'otp_option_two',
                'ntp_cmac',
                'cEdge_FNF_FTM_perf',
                'art',
                'bgp_model_cedge',
                'bridge_l2vpn_model_cedge',
                'bid_epc_cedge',
                'bid_epc_cedge_ipv6',
                'ospf_cli_template_cedge',
                'ospf_port_channel',
                'bsr_cli_template_cedge',
                'track_cli_template_cedge',
                'igmp_cli_template_cedge',
                'cfm_cli_template_cedge',
                'tunnel_cli_template_cedge',
                'central_sla_policy',
                'vman_sle',
                'vman_sle_new',
                'vman_platform_sle',
                'vman_sle_proxy',
                'sle_msla',
                'onprem_vman_sle',
                'mdp',
                'cedge_sig_tunnel_ecmp',
                'vedge_sig_tunnel_ecmp',
                'cedge_upgrade_sanity',
                'vSmartMaxPath',
                'ds_pcap_speed_vedge_cluster',
                'ds_speed_cedge_cluster',
                'intervrf_bgp_eigrp_cli_template_cedge',
                'intervrf_bgp_ospf_cli_template_cedge',
                'sdwan_rip_support_cedge',
                'rip_service_side',
                'sdwan_cts',
                'ErrorHandling',
                'aaa_cedge_enhance',
                'teacats',
                'cEdgePerformanceMonitor',
                'template_draft_mode',
                'sitSanity',
                'sitSanity_Dualtloc',
                'sdwan_cts_sxp',
                'vAnalytics',
                'sitAmazonSanity',
                'admintechprobe',
                'geofencing',
                'cedge_fnf_enhance',
                'dpi_aggregated_stats',
                'dpi_aggregated_stats_2010',
                'simulate_flows',
                'vEdge_Qos_Accuracy',
                'cEdge_sdwan_smu',
                'cEdgeNatDiaFlowStick',
                'viptela_upgrade_sanity',
                'aaa_vedge_rest',
                'aaa_cedge_rest',
                'cert_snmptraps',
                'syslog_new_rest',
                'cedge_syslog_rest',
                'vrrpv3_rest',
                'fwd_last_resort_rest',
                'vedge_last_resort_dev_sanity',
                'fwd_arp_and_app_rest',
                'EthchannelBasic',
                'EthchannelAdvanced',
                'EthchannelExtended',
                'EEM_sdwan',
                'teacat_CSCvx99236',
                'port_tracker',
                'port_tracker_vmanage',
                'port_tracker_scale',
                'dhcp_rest',
                'teacat_vedge_ipsec',
                'cedge_fnf_vpn0',
                'profileParcel',
                'vrrp_tracking_vmanage',
                'vrrp_tracking_vmanage_parcel',
                'vrrp_tracking_vmanage_vedge',
                'dhcp_cedge_rest',
                'dhcp_smart_relay',
                'default_aar_qos_policy',
                'vrrp_tracking_cedge',
                'tea_CSCvw96366',
                'cEdgePolicyAut',
                'PreUpgrade_MultiStepUpgrade_st',
                'PreUpgrade_MultiStepUpgrade_st_2',
                'cedge_cli_dispatch',
                'sdwan_comanagement',
                'sdwan_comanagement_ph2',
                'uc_sdwan_callerid_cli',
                'crl_certs',
                'vmanage_crl_quarantine',
                'te_app_sdwan_asr',
                'bid_condition_debug',
                'omp_teacat',
                'appqoe_ui',
                'device_error_propagation',
                'zbfw_interop',
                'platform_usb_disable',
                'platform_usb_disable_Mirabile',
                'cEdgePolicyPacketTaggingAut',
                'cEdge_forwarding_notifications',
                'cedge_forwarding_drop_statistics',
                'dhcp_vedge',
                'dhcp_cedge',
                'dhcp_cedge_vedge',
                'autonegotiation',
                'api_validation',
                'hsec_lic',
                'platform_service_timestamp',
                'cEdgeNatHSL',
                'vedge_packet_tracer_2',
                'alg_nat_zbfw',
                'alg_nat_zbfw_phase2',
                'cedge_packet_tag',
                'teacat_CSCwa48758',
                '1710_cedge_hard_scp_aux_tls',
                'vmanage_gui_cypress',
                'ux20_dual_device_workflow_cypress_DT',
                'ux20_simple_workflow_cypress_DT',
                'vmanage_gui_nms_cypress',
                'ux20_qos_cypress',
                'gui_cypress',
                'cedge_real_time_cflowd',
                'cedge_fnf_bfd_exporting',
                'cbug_ip_over_mpls',
                'cEdgeDestinationNAT',
                'cEdgeDestinationNAT_cli_template',
                'ux20_sdwan_troubleshooting_tools',
                'platform_sed',
                'cedge_fnf_max_cache',
                'dca_cedge_template_validation',
                'cedge_vfr_frag',
                'ipv6_gre_ipsec',
                'ipv6_604_606_gre_ipsec_tunnel',
                'FNF_vanalytics_enhance',
                'certificate_expiry_alarm',
                'boot_and_ping',
                'boot_and_ping_controllers',
                'user_password_expiry',
                'cData_wipe',
                'show_cpu_soc',
                'platform_power',
                'F104646_ConfigDiff_Policy',
                'tws_forensic',
            ]:
                if self.ppp:
                    protocol_yaml = 'pppoe_omp'
                else:
                    protocol_yaml = 'omp'
            elif protocol in ['ntp', 'ntp_rest']:
                protocol_yaml = 'ntp'
            elif protocol in [
                'cxp',
                'cxp_lb',
                'cxp_webex_cedge',
                'cxp_webex_sdavc',
            ]:
                protocol_yaml = 'cxp_2tloc'
            elif protocol in [
                'cxp_aut',
                'cxp_vpn0',
                'cxp_sig_manual_tunnel',
                'cxp_sig_auto_tunnel',
                'cxp_customapp',
                'cEdge_umts',
            ]:
                protocol_yaml = 'cxp'
            elif protocol in [
                'cxp_sig_loopback_DT',
                'cxp_sig_dialer_DT',
                'cxp_sig_subintf_DT',
            ]:
                protocol_yaml = 'cxp_3nat_wan_dual'
            elif protocol in ['crdc_vmanage_regression']:
                protocol_yaml = 'crdc_vmanage_regression'
            elif protocol in ['ofc365']:
                protocol_yaml = 'ofc365'
            elif protocol in ['ofc365_tel', 'ofc365_tel_ph4']:
                protocol_yaml = 'ofc365_tel'
            elif protocol in ['cxp_vedge', 'cxp_vedge_p0', 'cxp_vedge_sig', 'cxp_vedge_svc_vpn']:
                protocol_yaml = 'cxp_vedge'
            elif protocol in [
                'l7',
                'l7cEdge',
                'PBR_SIG',
                'l7vEdge_rest',
                'l7cEdge_rest',
            ]:
                protocol_yaml = 'l7'
            elif protocol in [
                'pfr',
                'max_n_sla_aar_policy_vedge',
                'cEdge_forwarding_notifications',
                'cedge_forwarding_drop_statistics',
                'gre',
                'gre_rest',
                'correlationEngine',
                'gui',
                'pfr_rest',
                'gui_st',
                'api_performance_cedge',
                'api_performance_vedge',
                'gui_cedge',
                'pppoe',
                'vexpress',
                'nExpress',
                'vEdgeLifeCycle',
                'alarms',
                'alarms_dev',
                'day0_workflow',
                'nExpress_robo',
                'nExpress_robot_mtt',
                'fwd_fec',
                'fwd_fec_1',
                'fwd_fec_new',
                'fwd_pkt_dup',
                'pathProbe',
                'fwd_fec_rest',
                'fwd_pkt_dup_rest',
                'cloudDock',
                'nExpress_clouddock',
                'network_design',
                'vman_cedge_cli_templates',
                'cedge_rfs_template',
                'pm_rfs_template',
                'nping_traceroute',
                'system_stats_verify',
                'vManage_compact_regression_20.3',
                'vManage_compact_regression_20.4',
                'vManage_compact_regression_20.5',
                'cert_enhancement',
                'ux_20_monitoring',
                'virtual_image_repo',
                'resource_monitoring',
                'device_group_tagging',
                'cEdgeDnsRedirect',
                'od_dpi',
                'vmanage_site_topology',
                'vmanage_password_policy',
                'device_group_tagging_rules',
                'device_group_tagging_phase2',
                'customizable_dashboard',
                'alarms_cedge',
                'alarms_vedge',
                'cEdgeManhattanFT_1M',
                'cEdgeManhattanFT_2T',
                'relqualify_next',
                'ux20_sdwan_troubleshooting_tools',
                'gre_in_udp',
                'rbac_device_variable',
                'rbac_comanagement_ph3',
                'Geofencing_cli_template_1t',
            ]:
                if self.ppp:
                    protocol_yaml = 'pppoe_omp_dual'
                else:
                    protocol_yaml = 'omp_dual'
                if self.include_sec_vb23:
                    protocol_yaml = 'gui_sw_vbond'
            elif protocol in ['unidScale']:
                protocol_yaml = 'scale_dual'
            elif protocol in ['cedge_eigrp', 'cedge_eigrp_rest']:
                protocol_yaml = 'cedge_eigrp'
            elif protocol in ['bgp_local_as']:
                protocol_yaml = 'bgp_local_as'
            elif protocol in ['tunnel_qos', 'adaptive_qos', 'tunnel_qos_express', 'adaptive_qos_express']:
                protocol_yaml = 'tunnel_qos'
            elif protocol in ['vpn_qos']:
                protocol_yaml = 'vpn_qos'
            elif protocol in ['policy_groups_qos', 'policy_groups_fnf']:
                protocol_yaml = 'cedge_dual_tloc_policy_qos'
            elif protocol in ['bgpv4v6']:
                protocol_yaml = 'bgp'
            elif protocol in ['bgp_prop_com', 'bgp_prop_com_cedge', 'bgp_prop_com_policy', 'bgp_prop_com_policy_rest']:
                protocol_yaml = 'bgp_prop_com'
            elif protocol in [
                'gwExpress',
                'gw_vmanage_rest',
                'amp',
                'sshkeylogin',
                'urlf_ips',
                'urlf_ips_basic',
                'urlf_ips_ids',
                'urlf_ips_interop',
                'gwExpress_robot',
                'gw_vmanage',
                'appfw_curl',
                'sig',
                'sig_ux2',
                'sig_ux2_p1',
                'sig_ux2_datapolicy',
                'security_policy_ux2_0',
                'security_policy_ux2_0_p0',
                'security_policy_ux2_0_p1',
                'security_policy_ux2_0_p2',
                'urlf_OpenDNS_nameserver_DT',
                'security_policy_ux2_0_cypress',
                'zbfw_custapp_ux2_0',
                'zbfw_ogref_ux2_0',
                'auto_tunnels_sig',
                'sig_umbrella_multiorg',
                'sigTracker_generic_cEdge',
                'sigTracker_generic_vEdge',
                'ssl_proxy_policy',
                'ssl_proxy_dp_policy',
                'ssl_proxy_sp_policy',
                'ssl_proxy_dp_sp_policy',
                'ssl_proxy_entropy_policy',
                'ssl_proxy_infra',
                'zbfw_fqdn',
                'zbfw_fqdn_basic',
                'zbfw_fqdn_interop',
                'umbrella_edns',
                'umbrella_edns_cedge',
                'umbrella_edns_vedge',
                'zbfw_vedge',
                'secPolicy',
                'nmap_utd',
                'zbfw_ruleset_lists',
                'gw_vmanage_rest_upgrade',
                'geo_filter',
                'L7tracker',
                'utd_unified_policy',
                'confd_ssr',
                'zbfw_utd_unified_logging',
                'unified_policy_ui',
                'unified_policy_rest',
                'greatwall_upgrade',
                'zbfw_ruleset_lists_scale',
                'zbfw_convert_customer_config',
                'sig_vedge',
                'L7tracker_cedge',
                'zbfw_reclassification',
                'unified_logging',
                'zbfw_ogref',
                'zbfw_ogref_1',
                'zbfw_ogref_2',
                'zbfw_master',
                'zbfw_ogref_scale',
                'zbfw_identity',
                'zbfw_identity_sgt',
                'zbfw_sgt_ux2_0',
                'zbfw_identity_ux2_0',
                'security_global_params',
                'security_global_params_basic',
                'security_global_params_reload',
                'sig_source_ecmp',
                'sig_tunnel_route_via',
                'gw_golden_rest',
                'sig_data_policy',
                'auto_zscaler_gre',
                'custom_signature',
                'utd_syslog',
                'security_mon_dashboard',
                'security_monitoring_vmanage_psv_stats',
                'ngfw_p0_sdwan',
                'utd_sig_rel_san',
            ]:
                protocol_yaml = 'gwExpress'
            elif protocol in ['gw_vmanage_mt']:
                protocol_yaml = 'gwExpress_mt'
            elif protocol in [
                'mt_edge_sanity',
                'mt_edge_device_life_cycle',
                'mt_edge_forwarding',
                'mt_edge_omp',
                'mt_edge_policy',
                'mt_edge_vdaemon',
                'mt_edge_tier',
                'mt_edge_implicit_acl',
                'vmanage_gui_nms_mt_cypress',
                'lawful_intercept_v2_mte',
                'lawful_intercept_v2_mtt',
            ]:
                protocol_yaml = 'mt_edge_prtcl'
            elif protocol in [
                'mtgw_qos_policy',
                'mt_edge_cflowd_stats',
            ]:
                protocol_yaml = 'gwExpress_mtgw_prtcl_barebone'
            elif protocol in ['pimMultiTloc', 'pimMultiTloc_rest']:
                protocol_yaml = 'omp_quad'
            elif protocol in [
                'tlocExt',
                'tlocExt_vedge_rest',
                'tlocExt_cedge_rest',
                'Flexible_Speedtest',
            ]:
                protocol_yaml = 'tlocExt'
            elif protocol in ['perfBed']:
                protocol_yaml = 'perf'
            elif protocol in ['cigna_pim']:
                protocol_yaml = 'cigna'
            elif protocol in ['wwan_qos', 'wwan','last_resort_circuit']:
                protocol_yaml = 'wwan'
            elif protocol in [
                'ompv4v6',
                'cEdgePolicyv4v6',
                'switchingv4v6',
                'forwardingv4v6',
                'ompv4v6_vedge_cli',
                'ompv4v6_cedge_cli',
                'ompv4v6_vedge_rest',
                'ompv4v6_cedge_rest',
                'forwardingv4v6_rest',
                'cedgeDualStack',
                'ipv6_nat_dia_P0',
            ]:
                protocol_yaml = 'omp_dual'
            elif protocol in [
                'vdaemonv4v6',
                'single_tenant_life_cycle',
                'vdaemoncEdge',
                'enterprise_certs',
                'enterprise_certs_csr',
                'vedge_enterprise_certs',
            ]:
                protocol_yaml = 'vdaemon_dual'
            elif protocol in ['proxy']:
                protocol_yaml = 'vdaemon_proxy_dual'
            elif protocol in ['mttproxy']:
                protocol_yaml = 'vdaemon_proxy_dual_mt'
            elif protocol in [
                'nExpress_mtt',
                'mttvbond',
                'multitenant',
                'gui_provider',
                'gui_tenant',
                'mtt_templates',
                'troubleshooting',
                'mtt_device_variable',
                'mtt_comanagement_ph3',
                'rbac',
                'mtt_device_life_cycle',
                'dr_mtt',
                'policy_builder',
                'policy_builder_vsmart_mtt',
                'mtt_maintenance',
                'mtt_parallel_tenant',
                'vman_feature_template_robot',
                'localized_policy_builder_mtt',
                'st_mtt_migration_st_setup_cleanup',
                'st_mtt_migration_mtt_setup_cleanup',
                'mtt_template_push_cedge',
                'nExpress_mtt_legacy',
                'virtual_image_repo_provider_mtt',
                'vmanage_remote_server',
            ]:
                protocol_yaml = 'hw_mtt' if self.tb.hw else 'mtt'
            elif protocol in ['mtt_dre']:
                protocol_yaml = 'mtt_appqoe_multisn_dre_proto'
            elif protocol in ['mtt_device_life_cycle_legacy']:
                protocol_yaml = 'hw_mtt' if self.tb.hw else 'mtt_legacy'
            elif protocol in [
                'cEdgeDual',
                'cEdgeFEC',
                'cEdgeFEC_rest',
                'cEdgeGre',
                'cedgev4v6',
                'cEdge_gre_in_udp_DT',
                'cedgev4v6_rest',
                'cedgeMulticastTlocExt',
                'cedgeMulticast',
                'cedgeMulticastTrigger',
                'cedgeMulticastSSM',
                'cedgeMulticastASM',
                'cedgeMulticastMH',
                'cedgeMulticastFull',
                'cedgeMulticastAutASM',
                'cedgeMulticast_pimbsr',
                'cedgeMulticast_msdp',
                'bgp_mpls',
                'cEdgePktDup',
                'aclRestAPI',
                'cEdgeClearDFbit',
                'pwk',
                'pwk_rekey_no_drop',
                'cEdgePolicyDual',
                'cEdgePolicyDual_policy',
                'cEdgePolicyDual_local_tloc',
                'cEdgePolicyDual_remote_tloc',
                'cEdgeDhcp_routetracker',
                'AARfromTunnel',
                'policies_log_action_DT',
                'cEdgeTcpopt',
                'cEdgeFwdServiceability',
                'policyMatchICMP',
                'policyMatchICMP_IPV6',
                'cEdgePolicyAAR',
                'max_n_sla_aar_policy',
                'bow_cli_template',
                'cEdgePolicyAARbow',
                'ipsec_serviceability',
                'deviceAclRestAPI',
                'deviceAclRestAPIipv6_cedge',
                'cEdgeCompactServices',
                'vEdgeAARBow',
                'cEdgeVedgeAarDpSlaAPrefCommonColor',
                'vEdgeCompactServices',
                'vEdgeCompactServices_rest',
                'cEdgePolicyRBAC',
                'bgp_mpls_rest',
                'cEdgePktDup_rest',
                'cEdgeAdaptiveFEC',
                'deviceAclRestAPI_vedge',
                'deviceAclRestAPI_cedge',
                'MIB_parity_178',
                'SdwanPolicyCAT',
                'ipv6_cedge_policy_app',
                'cedge_fnf_lpbk_as_tloc',
                'cEdgePolicyDNSPipeline',
                'teacat_cEdge',
                'cEdgePolicySdavcApp',
            ]:
                protocol_yaml = 'cedge_dual_tloc'
            elif protocol in [
                'cEdgeNatServiceSide',
                'cEdgeServiceSide_StaticNat_Datapolicy',
                'cEdgeNatServiceSide_IntraVPN',
                'cEdgeNatServiceSide_mte',
                'cEdgeNatServiceSide_FIS',
                'cEdgeNatDIAPortForwarding_cli',
                'cEdgeNatDIAPortForwarding_cli_template',
                'cEdgeNatDIAPortForwarding_restapi',
                'cEdgeNatGatekeeper',
            ]:
                protocol_yaml = 'cedge_dual_tloc_nat'
            elif protocol in ['cedgeMulticastAAR']:
                protocol_yaml = 'cedge_dual_tloc_aar'
            elif protocol in ['EdgeSymNat']:
                protocol_yaml = 'symnat'
            elif protocol in ['BfdTroubleshoot']:
                protocol_yaml = 'symnat'
            elif protocol in ['tlocOverNat']:
                protocol_yaml = 'tlocOverNat'
            elif protocol in ['DynamicTunnel']:
                protocol_yaml = 'dynamictunnel'
            elif protocol in ['perAppDscp']:
                protocol_yaml = 'perAppDscp'
            elif protocol in ['nat64']:
                protocol_yaml = 'cedge_dual_tloc_nat64'
            elif protocol in ['nat66_dia', 'nat66_dia_slaac_ra', 'nat66_dia_interface']:
                protocol_yaml = 'cedge_nat66_dia'
            elif protocol in ['nat66_dia_mlinks']:
                protocol_yaml = 'cedge_nat66_dia_multi_tloc'
            elif protocol in ['nat_v6tunnel', 'cEdgeNatPPPoE', 'ethernetPPPoE']:
                protocol_yaml = 'cedge_dual_tloc_ipv6_tunnel'
            elif protocol in ['AppPerfMonitor', 'nwpi_p4_global_topology', 'nwpi_global_topology_cypress']:
                protocol_yaml = 'cedge_dual_tloc_app_perf'
            elif protocol in ['omp_mtt']:
                protocol_yaml = 'omp_mtt'
            elif protocol in ['omp_feature']:
                protocol_yaml = 'omp'
            elif protocol in ['mtt_ztp']:
                protocol_yaml = 'mtt_ztp'
            elif protocol in ['dual_vedge_dual_site']:
                protocol_yaml = 'dual_vedge_dual_site'
            elif protocol in ['dual_vedge_tloc']:
                protocol_yaml = 'dual_vedge_tloc'
            elif protocol in ['nExpress_cluster']:
                protocol_yaml = 'vmanageScaling'
            elif protocol in ['cluster', 'cloudDock']:
                if self.include_scaling_vmanage6:
                    protocol_yaml = 'vmanageScaling_dual_tb69'
                elif self.include_scaling_vmanage:
                    protocol_yaml = 'vmanageScaling_dual'
                else:
                    protocol_yaml = 'omp_dual'
            elif self.include_scaling_vmanage:
                protocol_yaml = 'vmanageScaling'
            elif protocol in ['controlPlaneTroubleShooting']:
                protocol_yaml = 'affinity'
            elif protocol in ['forwardingUT']:
                protocol_yaml = 'forwardingUT'
            elif protocol in ['vdaemon_hardening']:
                protocol_yaml = 'gwExpress_vdaemon'
            elif protocol in ['affinity_hardening']:
                protocol_yaml = 'affinity_hardening'
            elif protocol in [
                'hsdwan',
                'hsdwan_direct_tunnels',
                'hsdwan_direct_tunnels_v6',
                'hsdwan_router_affinity',
                'hsdwan_policy',
                'hsdwan_vmanage',
                'hsdwan_transport_gw',
                'hsdwan_dp',
                'hsdwan_sanity_178',
                'hsdwan_dp_region_match',
                'hsdwan_v6',
                'hsdwan_router_affinity_v6',
            ]:
                protocol_yaml = 'hsdwan_omp'
            elif protocol in ['cedge_csc']:
                protocol_yaml = 'mpls_csc'
            elif protocol in ['ospf_cedge_rest']:
                protocol_yaml = 'ospf'
            elif protocol in ['bgpv4v6_rest', 'bgp_vedge_rest']:
                protocol_yaml = 'bgp'
            elif protocol in ['dhcpv6_sdwan_ipv6']:
                protocol_yaml = 'omp_dual_tloc_in_single_inet'
            elif protocol in ['vmanage_remote_server_st']:
                protocol_yaml = 'omp'
            elif protocol in ['lawful_intercept_v2']:
                protocol_yaml = 'cedge_dual_tloc_li'
            elif protocol in ['SmartPinning']:
                protocol_yaml = 'smartpinning'
            elif protocol in [
                'cEdgeNATBFDPortPreservation',
                'cEdgeNATBFDPortPreservation_cli_template',
            ]:
                protocol_yaml = 'nat_bfd_preservation'
            elif protocol in ['cedge_vmanage_fwd_class_aut', 'cedge_vmanage_fwd_class_DT']:
                protocol_yaml = 'omp'
            elif protocol in ['log_action']:
                protocol_yaml = 'omp'
            elif protocol in ['transport_Etherchannel']:
                protocol_yaml = 'omp_transport_ether'
            elif protocol in ['predictiveNetworks_DT']:
                protocol_yaml = 'wani'
            else:
                if self.ppp:
                    protocol_yaml = protocol +'_pppoe'
                elif self.include_vs20:
                    protocol_yaml = protocol +'_ivs20'
                else:
                    protocol_yaml = protocol
                    if self.reverse_proxy:
                        protocol_yaml = '%s_proxy'%(protocol)
        return protocol_yaml

    def _protocol_yaml_full_path(self, fpath):
        if '/' in fpath:
            yaml_file = str(Path(fpath).with_suffix('.yaml'))
        else:
            yaml_file = str(Paths().protocols(fpath).with_suffix('.yaml'))
        return yaml_file

    def instantiate_api(self, protocol, yaml, file_path):
        '''Returns "api", which is an  instance of "Tests"'''
        if self.runner_systb:
            # setup the necessary stuff for a system bed
            if self.tb.manage_system_lock('try_lock'):
                self.tb.manage_system_lock('create_lock')
            else:
                self.logger.error('ERROR: Testbed %s not available' % self.runner_systb[0])
                return -99
            api = self.api
            api.set_machines_list(list(self.tb.machines().keys()))
            return api

        # If we're not running a system bed, setup env for a local tb

        ###
        # Protocol Yaml specification order of precedence:
        # 1. Command line argument
        # 2. TTF (suite)
        # 3. Other:
        #    - Hard-coded from `get_protocol_yaml()` (deprecated),
        #    - A testbed-specific yaml if it exists,
        #    - Protocol yaml with the same name as the suite (last resort)
        ###
        if self.args.protocol_yaml:
            yaml_file = self._protocol_yaml_full_path(self.args.protocol_yaml)
        elif self.args.ttf.protocol:
            # It is specified in the TTF
            yaml_file = self._protocol_yaml_full_path(self.args.ttf.protocol)
        else:
            yamls_dir = str(Paths().protocols())
            protocol_yaml = self.get_protocol_yaml(protocol)
            # If no yaml file is specified look for one under vtest/yamls/protocols
            # Check for a yaml file with the same name as the script
            if yaml is None:
                # If there is a yaml file with the name of the testbed in it use that one over the regular one
                specific_config = os.path.join(yamls_dir, '%s_%s.yaml' % (self.tb_hostname, protocol_yaml))
                if os.path.isfile(specific_config):
                    yaml_file = specific_config
                else:
                    yaml_file = os.path.join(yamls_dir, '%s.yaml' % protocol_yaml)
            else:
                # If a yaml file is specified but it is not the entire path to the yaml file
                # then add the string, sepcified in yaml, to the name of the yaml file
                if yaml.endswith('.yaml') is False:
                    yaml_file = os.path.join(yamls_dir, '%s_%s.yaml' % (protocol_yaml, yaml))
                else:
                    yaml_file = yaml
            self.logger.debug('yaml: %s' % yaml)
        self.logger.info("Protocol YAML: {}".format(yaml_file))
        self.args.protocol_yaml = yaml_file
        api = None
        # If the yaml file exists and tests are not running against remote vmanage, load it and parse it using the api class
        if os.path.isfile(yaml_file):
            api = Tests(
                yaml_file, self.tb.reserved_vpn_list, self.tb.vpn, self.trans_ipv6, self.ipv6_ra, self.serv_ipv6
            )
            self.logger.debug('Yaml file exists')
        else:
            if yaml is not None:
                self.logger.info('ERROR: Yaml file specified but could not be found; %s' % yaml_file)
                return -99
            self.logger.info('Yaml file not found, continuing without it')
        # If we have created an instance of the api class then give it a list of the names of all the machines
        if api is not None:
            if not self.include_vmanage and protocol not in [
                'vmanage_sdwan',
                'vmanage_gui',
                'cert_mgmt',
                'gui',
                'vman_omp_template',
                'vman_omp_cfg_templ',
                'vman_ztp_omp_cfg_templ',
                'vs_gui_policy',
                'correlationEngine',
                'ztp',
                'vman_certs',
                'vman_certs_revamp',
                'rbac_device_variable',
                'rbac_comanagement_ph3',
                'apps_performance',
                'apps_performance_206',
                'rbac_comanagement_ph3_cluster',
                'vexpress',
                'multitenant',
                'gui_st',
                'gui_cedge',
                'gui_provider',
                'gui_tenant',
                'mtt_templates',
                'troubleshooting',
                'rbac',
                'policy_builder',
                'policy_builder_vsmart_mtt',
                'mtt_maintenance',
                'mtt_parallel_tenant',
                'vman_feature_template_robot',
                'mtt_template_push_cedge',
                'virtual_image_repo_provider_mtt',
                'virtual_image_repo',
                'api_performance_vedge',
                'virtual_image_repo_provider_mtt',
                'api_performance_cedge',
                'rbac_device_variable_cluster',
            ]:
                self.logger.info(
                    '****** Deleting vmanage from protocol yaml. Please specify -ivm to run tests with vmanage. ******'
                )
                api.delete_vmanage_parameters()
            api.set_machines_list(list(self.tb.machines().keys()))
        return api

    def create_vmanage_sessions(self, no_init=False):
        # Create an instance for VMANAGESession
        cookie_dir = str(Paths().vtest('http_cookies'))
        try:
            os.mkdir(cookie_dir)
        except OSError:
            pass
        api_cookie_path = os.path.join(cookie_dir, 'api')
        if not os.path.exists(api_cookie_path):
            os.mkdir(api_cookie_path)
        http_cookie_path = os.path.join(cookie_dir, 'http')
        if not os.path.exists(http_cookie_path):
            os.mkdir(http_cookie_path)
        http_password = self.password
        vmanage = Machines().get_vmanage()
        if vmanage and not no_init:
            try:
                self.logger.info("create_vmanage_sessions")
                self.logger.info(f"create_vmanage_sessions, http_password: {http_password}")
                with vmanage.get_http(polling_login=False) as http:
                    self.logger.info(f"create_vmanage_sessions: {vmanage}: {http.get_version()}")
                    print(f'{vmanage}: {http.get_version()}')
            except Exception:
                self.logger.info("create_vmanage_sessions, poll_ready")
                vmanage.poll_ready(timeout=3600, blind_wait_time=0)
            with vmanage.get_http():
                self.logger.info("create_vmanage_sessions, vmanage.get_http()")
                # get_http() will have performed password change, if required
                http_password = vmanage.get_http_password()
                self.logger.info(f"create_vmanage_sessions, http_password: {http_password}")
        tb = self.tb
        if self.runner_systb is not None:
            http_api = VMANAGESession_system(
                tb, self.logger, self.http_debug, self.http_debug, self.http_debug, http_cookie_path, self.logs_sub_dir
            )
        else:
            http_api = VMANAGESession(
                tb, self.logger, self.http_debug, self.username, http_password, self.vmanage_ips, skip_init=no_init
            )

        session_config = tb.config.get('vmanage_session_config')
        if not session_config or no_init:
            vman_session = None
        else:
            vmanages_info = {}
            for hostname in tb.get_vmanage_machine(True):
                domain_ip = tb.mgmt_ipaddr(hostname)
                vmanage_machine = Machines().get(hostname)
                vmanages_info[hostname] = {
                    'mgmt_ip': domain_ip,
                    'domain_name': domain_ip,
                    'username': vmanage_machine.get_http_username(),
                    'password': vmanage_machine.get_http_password(),
                }
            vman_session = VManageSession(vmanages_info, session_config['provider_domain_name'])
        ssh = VmanageSSH(self.logger, self.vmanage_ips, self.username, self.password)

        if vmanage and not no_init:
            with vmanage.get_http() as http:
                ver_full = http.get_version()
                ver_short = '.'.join(ver_full.split('.')[:2])
                if (
                    compare_version(ver_short, '20.18', op.ge)
                    and GlobalParam().okta_config.enable
                    and not OktaAuth().authenticate()
                ):
                    self.logger.info('Okta authentication failure - see okta_auth.log')
                forced = os.getenv('VMANAGE_FORCE_ENABLE_NG_TEMPLATE_SUPPORT') is not None
                forced_msg = '(forced by VMANAGE_FORCE_ENABLE_NG_TEMPLATE_SUPPORT in env) '

                self.logger.debug("NG template forced: {}".format(forced))
                self.logger.debug("vManage {} version {} (short {})".format(vmanage.name, ver_full, ver_short))

                if compare_version(ver_short, '20.15', op.ge) or forced:
                    # check if API is present as it was added in 20.15.3
                    api_present = http._check_enableTemplateSupport()
                    self.logger.debug("NG template API present: {}".format(api_present))
                    if api_present or forced:
                        self.logger.info(
                            "vManage {} runs {} and NG template API is present hence calling {} hidden API to enable ng_template_support".format(
                                vmanage.name, ver_short, forced_msg if forced else ''
                            )
                        )
                        self.logger.info("Initial ng_template_support={}".format(http._get_ng_template_support()))
                        self.logger.info("Result of set_ng_template_support={}".format(http._set_ng_template_support()))
                        if not http._get_ng_template_support():
                            self.logger.error("Enable NG tempalate support is still not enabled")

        return {
            'http_api': http_api,
            'http_password': http_password,
            'vman_session': vman_session,
            'ssh': ssh,
        }

    def create_confd_sessions(self, script, no_init=False):
        # Close any open expect sessions and their log files
        # CHANGE: consider re-using the sessions if possible, just change the log files
        try:
            self.close_all_machine_sessions()
        except AttributeError:
            pass

        # Create, regular and root, sessions for all the machines
        # Use multithreading to make it much faster

        confd_machine_sessions = {}
        # Get regular confd sessions
        res = self.tb.get_all_mchs_sessions(self.logs_sub_dir, 'confd-%s' % script, no_init=no_init)
        if res == -99:
            return res
        confd_machine_sessions = res
        # Get root sessions
        res = self.tb.get_all_mchs_sessions(self.logs_sub_dir, 'tb-%s' % script, root=True, no_init=no_init)
        if res == -99:
            return res
        self.root_sessions = res
        # Get ncs sessions
        res = self.tb.get_all_mchs_sessions(self.logs_sub_dir, 'ncs-%s' % script, ncs=True, no_init=no_init)
        if res == -99:
            return res
        self.ncs_sessions = res
        # Get iosXE sessions for cisco devices
        iosxe_cli_sessions = self.tb.get_all_iosxe_cli_sessions(self.logs_sub_dir, 'iosxe-%s' % script, no_init=no_init)
        # Create sessions dictionary
        self.sessions = {
            'confd': confd_machine_sessions,
            'root': self.root_sessions,
            'ncs': self.ncs_sessions,
            'iosxe': iosxe_cli_sessions,
        }

        self.transport_machine_sessions = {}

        # CHANGE: need to add comments for this
        if self.tb.dynamips_config():
            dynamips_routers, dynamips_sessions = self.tb.dynamips_sessions()
            for router, session in zip(dynamips_routers, dynamips_sessions):
                cmd = 'telnet localhost '
                dyna_log = os.path.join(self.logs_sub_dir, '%s-dynamips-%s.log' % (router, script))
                dyna_log_fd = open(dyna_log, 'w')
                cmd += session
                dyna_child = pexpect.spawn(
                    cmd, timeout=25, logfile=dyna_log_fd, encoding='utf-8', codec_errors='ignore'
                )
                dyna_child.sendline('\r\n')
                dyna_child.flush()
                time.sleep(2)
                if self.debug:
                    dyna_child.logfile = sys.stdout
                try:
                    index = dyna_child.expect(['Username: ', '%s>' % router, '%s#' % router])
                    if index == 0:
                        dyna_child.sendline('cisco\r\n')
                        dyna_child.expect(['Password: '])
                        dyna_child.sendline('cisco\r\n')
                        dyna_child.expect(['%s>' % router])
                        dyna_child.sendline('enable\r\n')
                        dyna_child.expect(['Password: '])
                        dyna_child.sendline('cisco\r\n')
                        dyna_child.expect(['%s#' % router])
                    elif index == 1:
                        dyna_child.sendline('enable\r\n')
                        dyna_child.expect(['Password: '])
                        dyna_child.sendline('cisco\r\n')
                        dyna_child.expect(['%s#' % router])
                except pexpect.EOF:
                    self.logger.error('ERROR: Dynamips session for %s could not be established' % router)
                    return -99
                self.transport_machine_sessions[router] = dyna_child
                # self.expect_logs.append(dyna_log_fd)
                logging.info('Successfully added Dynamips-session for %s' % router)

    def create_ultimate(self, protocol, file_path, script_name, no_init=False):
        """
        Creates a dictionary of imported classes to be passed to test suites
        """
        ultimate = {}

        tb = self.tb
        api = self.api
        script = script_name
        if not self.runner_systb:
            if protocol not in script_name:
                script = script_name + '-' + protocol
            # tb.create_machine_log_folders()
            for mch in tb.machines():
                machine_log_path = os.path.join(self.logs_sub_dir, mch)
                # self.tb.mkpath(machine_log_path)
                tb_expect_log = os.path.join(machine_log_path, '%s-tb-%s.log' % (mch, script))
                # tb_expect_log = os.path.join(machine_log_path, 'tb.log')
                # For each machine pass the tb-log location to testbed
                # This allows us to use the same log file for all shell commands, whether it is through runner or testbed
                # CHANGE: Consider moving this to the next for loop
                self.tb.set_log_file_for_mch(tb_expect_log, mch)

        # populates self.sessions
        if self.create_confd_sessions(script, no_init=no_init) == -99:
            return -99

        pigeon = {}
        pigeon['logs_sub_dir'] = self.logs_sub_dir
        # Create an instance of confd_session with all the pexpect machine sessions that we just created
        confd = CONFDSession(
            tb,
            self.sessions,
            self.logger,
            api,
            self.encap,
            None,  # no http_api present yet
            pigeon,
            self.vmanage_ips,
            self.tcp_opt,
            self.config_sync,
            self.ikev2,
            self.ikev1_aggressive,
        )
        self.confd = confd
        try:
            vmanage_sessions = self.create_vmanage_sessions(no_init=no_init)
        except Exception as e:
            # Go and grab logs from vManage for above exception
            vmanage = Machines().get_vmanage().name
            dst = os.path.join(
                self.logs_sub_dir, vmanage, f'create_vmanage_sessions_{vmanage}-admin-tech', 'admin-tech.tar.gz'
            )
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)
            try:
                self.logger.error(
                    f"Couldn't create vManage({vmanage}) http session due to following exception:\n{str(e)}."
                )
                self.logger.info(f'Collecting admin techs logs from {vmanage}.')
                self.get_admin_tech(vmanage, dst)
                self.logger.info(
                    f'Admin techs logs after issues with creating vManage({vmanage}) session are in {dst_dir}'
                )
            except Exception as ee:
                self.logger.error(
                    f'Unfortunately could not get admin techs logs after issues with creating vManage({vmanage}).'
                )
                self.logger.error(str(ee))
            finally:
                # Try to diagnose the vManage
                diagnose_vmanage(self.logger, dst_dir)
                raise e

        http_api = vmanage_sessions['http_api']
        vman_session = vmanage_sessions['vman_session']

        # Update confd object as we have http_api
        self.confd.http = http_api

        if no_init:
            self.crft = False
            self.nrcc = True
            self.ss = None
            ultimate['api'] = api
            ultimate['confd'] = self.confd
            ultimate['http'] = http_api
            ultimate['logger'] = self.logger
            ultimate['sessions'] = self.sessions
            ultimate['tb'] = self.tb
            ultimate['vman_session'] = vman_session
            return ultimate

        #Create an instance of iosxe_session
        iosxe = IOSXESession(tb, self.sessions, self.logger, api, self.encap, http_api, pigeon, self.vmanage_ips, self.tcp_opt)
        # Create an instance of viptela_session, pass in the instance of confd_session we just created
        vs = ViptelaSession(tb, api, self.logger, confd, self.print_netconf, self.snmpv3, http_api, vman_session, iosxe)
        if subprocess.call(['which', 'jmeter']) != 0:
            jmeter_session = None
        else:
            jmeter_session = JmeterSession(tb, self.logger, self.logs_sub_dir, vs, confd, self.vmanage_ips, http_api)
        # Initialize xml generator
        xml = XMLgenerator(http_api, self.vmanage_ips, logger=self.logger)
        #Create an instance of ConfigBuilder, pass in all the pexpect machine sessions that we just created
        netconf_list = []
        if self.api is not None:
            for machine in self.api.machines():
                if self.api.config_type(machine) == 'netconf':
                    netconf_list.append(machine)
        cb = Configbuilder(tb, netconf_list, vs, api, self.sessions, self.transport_machine_sessions, xml)
        # IOS-XE netconf session based out of Configbuilder
        ncs_xe = IOSXENetconf(tb, netconf_list, vs, api, self.sessions, self.transport_machine_sessions, xml, iosxe)
        # Create an instance for cisco
        cs = CiscoSession(tb, self.logger)
        robot_session = RobotSession(tb, self.logger)
        if self.restapi:
            routingrest = RoutingVmanageREST(tb, api, http_api, vman_session, self.logger, confd, iosxe)
        else:
            routingrest = None
        if self.restapi:
            servicesrest = ServicesVmanageREST(tb, api, http_api, vman_session, self.logger, confd, iosxe)
        else:
            servicesrest = None
        if self.restapi:
            forwardingrest = ForwardingVmanageREST(tb, api, http_api, vman_session, self.logger, confd, iosxe)
        else:
            forwardingrest = None
        if self.restapi:
            policyrest = PolicyVmanageREST(tb, api, http_api, vman_session, self.logger, confd, iosxe)
        else:
            policyrest = None
        if self.restapi:
            mtpolicyrest = MTPolicyVmanageREST(http_api, confd, self.logger)
        else:
            mtpolicyrest = None
        if self.restapi:
            mtforwardingrest = MTForwardingVmanageREST(tb, api, http_api, vman_session, self.logger, confd, iosxe)
        else:
            mtforwardingrest = None
        # Create an instance of wwan session for wwan suite only
        if self.suite in ['wwan_qos', 'wwan', 'last_resort_circuit']:
            wwans = WWANSession(
                tb,
                confd,
                vs,
                self.logger,
                self.logs_sub_dir,
                self.sku,
                self.wwan_sku,
                self.network_bw,
                self.dual_tloc,
                self.tcp_opt,
                iosxe,
            )
        else:
            wwans = None

        # Create an instance of landslide session for wlan suite only
        if self.suite in ['wlan']:
            ls = LandslideSession(
                tb.landslide_server_ip(),
                tb.landslide_username(),
                tb.landslide_password(),
                self.logger,
                self.logs_sub_dir,
            )
        else:
            ls = None

        vmanage_present = self.include_vmanage or protocol == 'vmanage_sdwan'
        css = CombinedShowSession(vs, http_api, confd, api, vmanage_present)
        vgs_cookie_path = str(Paths().vtest('http_cookies/vgs'))
        if not os.path.exists(vgs_cookie_path): os.mkdir(vgs_cookie_path)
        vgs = VmanageGUISession(tb, self.logger, vgs_cookie_path, http_api, self.show_display)
        temp_js_dir = str(Paths().scripts("protractor/configs"))
        try:
            os.mkdir(temp_js_dir)
        except OSError:
            pass
        if subprocess.call(['which', 'protractor']) != 0:
            ps = None
        else:
            selenium_address = pref.get('selenium_address')
            selenium_port = pref.get('selenium_port')
            win_selenium_address = pref.get('windows_selenium_address')
            win_selenium_port = pref.get('windows_selenium_port')
            if len(self.browser) == 0:
                self.browser = ['chrome']
            if self.run_selenium_on_windows is False:
                #Initialize protractor ubuntu session
                if len(self.vmanage_ips) > 0:
                    vmanage_ip = self.vmanage_ips[0]
                else:
                    vmanage_ip = None
                ps = ProtractorSession(
                    tb,
                    self.logger,
                    script_name,
                    temp_js_dir,
                    self.logs_sub_dir,
                    selenium_address,
                    selenium_port,
                    self.browser,
                    vs,
                    confd,
                    vmanage_ip=vmanage_ip,
                )
            else:
                # Initialize protractor windows session
                ps = ProtractorSession(
                    tb,
                    self.logger,
                    script_name,
                    temp_js_dir,
                    self.logs_sub_dir,
                    win_selenium_address,
                    win_selenium_port,
                    self.browser,
                    vs,
                    confd,
                    windows_machine=True,
                )
        # Figure out the paths to the config files to use, in case we want to do a setup by loading the files
        config_files_path = os.path.join(os.path.dirname(file_path), 'setup_configs')
        config_files_path = os.path.join(config_files_path, script_name)
        #Put all the information that we will need in any of the scripts, all the instances that we just created, in a dictionary
        #Add systb to ultimate only if tests are running on system testbed
        if tb.is_nat() or tb.tb_is_branch('14.1_or_lower') or protocol == 'pim' or self.ppp or protocol == 'affinity':
            self.transport_routing = False
        if tb.is_nat() or tb.tb_is_branch('14.1_or_lower') or protocol != 'forwarding':
            self.internal_nat = False

        ultimate = {
            'tb': tb,
            'api': api,
            'old_ver': self.vmanage_version_compare,
            'jmeter': True if jmeter_session else False,
            'jmeter_session': jmeter_session,
            'run_jmeter': True if jmeter_session else False,
            'vmanage_ips': self.vmanage_ips,
            'confd': confd,
            'netconf': netconf_list,
            'cb': cb,
            'vs': vs,
            'cs': cs,
            'routing_restapi': routingrest,
            'policy_restapi': policyrest,
            'mtpolicy_restapi': mtpolicyrest,
            'forwarding_restapi': forwardingrest,
            'mtforwarding_restapi': mtforwardingrest,
            'services_restapi': servicesrest,
            'robot_session': robot_session,
            'protocol': protocol,
            'sessions': self.sessions,
            'transport_sessions': self.transport_machine_sessions,
            'configs': config_files_path,
            'ss': self.ss,
            'ixias': self.ixias,
            'ubuntu': self.ubuntu,
            'ise': self.ise,
            'ad': self.ad,
            'fwconfig': self.fwconfig,
            'non_dmz': self.non_dmz,
            'restapi': self.restapi,
            'cli_template': self.cli_template,
            'branch': self.branch,
            'utd_tar_branch': self.utd_tar_branch,
            'utd_tar_image': self.utd_tar_image,
            'trex': self.trex,
            'trex_stl': self.trex_stl,
            'trex_stf': self.trex_stf,
            'pagent': self.pagent,
            'rtc': self.random_tloc_color,
            'transport_routing': self.transport_routing,
            'transport_vpn': self.transport_vpn,
            'internal_nat': self.internal_nat,
            'cflowd_transport_udp': self.cflowd_transport_udp,
            'symmetric_nat': self.symmetric_nat,
            'dpi': self.dpi,
            'tls': self.tls,
            'nrcc': self.nrcc,
            'encap': self.encap,
            'var_dict': self.var_dict,
            'tcp_opt': self.tcp_opt,
            'bridge': self.bridge,
            'mcast': self.mcast,
            'cellular': self.cellular,
            'wlan_country': self.wlan_country,
            'sku': self.sku,
            'wwan_sku': self.wwan_sku,
            'network_bw': self.network_bw,
            'dual_tloc': self.dual_tloc,
            'mtu_range': self.mtu_range,
            'serial_type': self.serial_type,
            'partner_type': self.partner_type,
            'trans_ipv6': self.trans_ipv6,
            'ipv6_ra': self.ipv6_ra,
            'serv_ipv6': self.serv_ipv6,
            'ipv6': self.ipv6,
            'vsmart_policy_builder': self.vsmart_policy_builder,
            'http': http_api,
            'css': css,
            'ppp': self.ppp,
            'suppress_missing_node_msg': [False],
            'vgs': vgs,
            'wwans': wwans,
            'ps': ps,
            'ls': ls,
            'include_vs4': self.include_vs4,
            'include_vs20': self.include_vs20,
            'include_scaling_vmanage': self.include_scaling_vmanage,
            'include_scaling_vmanage6': self.include_scaling_vmanage6,
            'version_to_download': self.version_to_download,
            'cedge_version_upgrade': self.cedge_version_upgrade,
            'cxp_latency': self.cxp_latency,
            'non_dmz_ip': self.non_dmz_ip,
            'ubuntu_client_dns_resolver_ip': self.ubuntu_client_dns_resolver_ip,
            'edge_name_server_ip': self.edge_name_server_ip,
            'cxp_loss_percentage': self.cxp_loss_percentage,
            'secret_access_aws': self.secret_access_aws,
            'vmanage_version_upgrade': self.vmanage_version_upgrade,
            'dut': self.args.dut,
            'cli_message': self.args.message,
            'label': self.label,
            'vedge_version_upgrade': self.vedge_version_upgrade,
            'aon_eio_version_upgrade': self.aon_eio_version_upgrade,
            'cedge_cleanup': self.cedge_cleanup,
            'ucs_cleanup': self.ucs_cleanup,
            'cedge_container_upgrade': self.cedge_container_upgrade,
            'vedge_mips_upgrade': self.vedge_mips_upgrade,
            'image_to_download': self.image_to_download,
            'snmpv3': self.snmpv3,
            # 'vcontainer': self.vcontainer,
            'xml': xml,
            'logger': self.logger,
            'transport': self.transport,
            'ikev1_aggressive': self.ikev1_aggressive,
            'ikev2': self.ikev2,
            'exclude_browser': self.exclude_browser,
            'logs_sub_dir': self.logs_sub_dir,
            'no_caserver': self.no_caserver,
            'reverse_proxy': self.reverse_proxy,
            'mt_proxy': self.mt_proxy,
            'enable_cisco_hosted': self.ech,
            'selinux': self.selinux,
            'abort_parallel': self.abort_parallel,
            'iosxe': iosxe,
            'ncs_xe': ncs_xe,
            'utd_profile': self.utd_profile,
            'cisco_pki': self.cisco_pki,
            'uar': self.uar,
            'pdc': self.pdc,
            'pdv': self.pdv,
            'pdvc': self.pdvc,
            'pwka': self.pwka,
            'ent_certs': self.ent_certs,
            'vsmoke': self.vsmoke,
            'level': self.level,
            'fw_pkgs': self.fw_pkgs,
            'vtest_dir': str(Paths().vtest()),
            'runner': self,
            'ux2': self.ux2,
            'cellular_slot': self.cellular_slot,
            'mtedge_vrf_count': self.mtedge_vrf_count,
            'mtedge_tenant_mode': self.mtedge_tenant_mode,
            'mtedge_trans_ipv4': self.mtedge_trans_ipv4,
            'mtedge_serv_ipv4': self.mtedge_serv_ipv4,
            'mtedge_trans_ipv6': self.mtedge_trans_ipv6,
            'mtedge_serv_ipv6': self.mtedge_serv_ipv6,
            'qos_throughput': self.qos_throughput,
            'runsuite': False,
            'sig_tunnel_type': self.sig_tunnel_type,
            'ips_sig': self.ips_sig,
            'unid_platform': self.unid_platform,
            'reserve_org_name': self.reserve_org_name,
        }
        ultimate.update(vmanage_sessions)

        return ultimate

    def determine_dut_hosts(self):
        '''
        Returns list of names of machines considered as DUTs.
        If user specified -dut or --dut from command line , it takes precedence
        over TTF and defaults.
        '''
        # passed via '-dut' or --dut
        if self.args.dut:
            dut_hosts = [d.strip() for d in self.args.dut.split(',') if d]
            self.logger.debug('Using user specifed DUTs: %s', dut_hosts)
        elif len(self.args.ttf.dut_hosts) > 0:
            dut_hosts = self.args.ttf.dut_hosts[:]
            self.logger.debug('Using TTF specifed DUTs: %s', dut_hosts)
        else:
            dut_hosts = ['vm5', 'pm5']
            self.logger.debug('Using defaults for DUTs: %s', dut_hosts)
        return dut_hosts

    def get_dut_hosts(self, sanity_check=True):
        '''
        Returns list of names
        '''
        dut_hosts = self.determine_dut_hosts()
        if sanity_check:
            machines = set(self.sessions['confd'])
            hosts = set(dut_hosts)
            not_in_machines = hosts - machines
            if not_in_machines:
                dut_hosts = list(hosts & machines)
                self.logger.warning('DUT machine(s) %s not in the machine session list %s', not_in_machines, machines)
        return dut_hosts


    def final_version_checks(self):
        if not self.version_checked or self.args.skip_legacy:
            return
        tb_machines = self.tb.machines()
        for m in self.sessions['confd']:
            # it means that someone injected session , i.e. form test case code.
            if m not in tb_machines:
                self.logger.debug("[final_version_checks] machine {} not found in topology".format(m))

        # check versions only on sessions for machines that are part of topology
        changed = self.check_versions([m for m in self.sessions['confd'] if m in tb_machines])
        if not changed:
            return

        self.dtdash_dict['nodes'] = self.node_info
        self.save_dt_dash()
        if self.db_write and self.db_build_id:
            try:
                with self.get_db_client() as db_handle:
                    db_handle.push_node_info_to_db(self.db_build_id, self.node_info)
                    # To consider: this moment could be the one right to track update versions
                    db_handle.update_build_to_db(self.db_build_id, self.db_build, self.db_tb_name)
            except Exception:
                self.logger.warning("Error inserting data to regressdb", exc_info=True)

    def initial_version_checks(self):
        # If we haven't checked the version yet, go ahead and do it
        # We have the self.version_checked variable since we call this function once for every script we run but we only need to do the version check once
        if self.version_checked:
            return

        self.dut_image_versions = set()
        self.versions = set()
        self.non_vmanage_versions = set()
        self.vmanage_versions = set()
        self.node_info = {}

        tb_machines = self.tb.machines()

        for m in self.sessions['confd']:
            # it means that someone injected session , i.e. form test case code.
            if m not in tb_machines:
                self.logger.debug("[initial_version_checks] machine {} not found in topology".format(m))

        # check versions only on session for machines that are part of topology
        return self.check_versions([m for m in self.sessions['confd'] if m in tb_machines])

    def check_versions(self, machines):
        '''Returns: False if no versions changed since last invocation otherwise True'''
        # Use sets to figure out if we have more than one version
        changed = False
        has_any_error = False
        versions = set()
        non_vmanage_versions = set()
        vmanage_versions = set()
        dut_image_versions = set()

        self.logger.info('\n')
        self.logger.info('IMAGE VERSIONS:')
        # For each machine get the version
        threads = []
        for machine in machines:
            thread = VersionCheckThread(machine, self)
            thread.start()
            thread.t_start = time.time()
            threads.append(thread)
        for i, thread in enumerate(threads, start=1):
            self.logger.debug("Thread on machine {} to be joined ({}of{})".format(thread.machine, i, len(threads)))
            # It was measured that ~10 seconds is needed to finish the thread
            # Using timeout  of 60 seconds as countermeasure for deadlocked threads (for any reason)
            thread.join(timeout=60)
            thread.t_end = time.time()
            t_status_done = 'not' if thread.is_alive() else ''
            msg = "Thread on machine {} {} done in {}s".format(
                thread.machine, t_status_done, thread.t_end - thread.t_start
            )
            if t_status_done:
                self.logger.error(msg)
                self.logger.warning(
                    "Not joined thread on machine {} can cause issues at the end of runner execution".format(
                        thread.machine
                    )
                )
            else:
                self.logger.debug(msg)

            if thread.message:
                if thread.has_error:
                    self.logger.error(thread.message)
                else:
                    self.logger.info(thread.message)

            if thread.has_error:
                # info if present logged above
                has_any_error = True
                continue

            versions = versions.union(thread.versions)
            non_vmanage_versions = non_vmanage_versions.union(thread.non_vmanage_versions)
            vmanage_versions = vmanage_versions.union(thread.vmanage_versions)

        self.logger.info('\n')
        self.logger.info('PLATFORMS:')
        dut_hosts = self.get_dut_hosts()
        for thread in threads:
            self.node_info[thread.machine] = {
                'node_type': thread.platform,
                'image_version': thread.image_version,
                "modems": thread.modems_pids,
                'dut': False,
            }
            self.logger.info("{}: {}".format(thread.machine, thread.platform))
            if thread.machine in dut_hosts:
                self.node_info[thread.machine]['dut'] = True
                dut_image_versions.add(thread.image_version)

        db_build = ','.join([v for v in dut_image_versions if v is not None])
        if not db_build:
            self.logger.warning("Couldn't find DUTs' OS version - NOT setting self.db_build")
        else:
            if not self.db_build:
                self.logger.debug(f'Setting self.db_build to: {db_build}')
            else:
                if dut_image_versions != set(self.dut_image_versions):
                    changed = True
                    self.logger.info(f'self.db_build changed: {self.db_build} --> {db_build}')
            self.db_build = db_build

        self.logger.info('\n')

        self.logger.info('DUTS:')
        if not dut_image_versions:
            self.logger.warning('DUT not found')
        for m, info in self.node_info.items():
            if info['dut']:
                self.logger.info("DUT: {}".format(m))
        self.logger.info('\n')

        if self.dut_image_versions:
            comparisons = [
                (versions, self.versions, 'versions'),
                (non_vmanage_versions, self.non_vmanage_versions, 'non_vmanage_versions'),
                (vmanage_versions, self.vmanage_versions, 'vmanage_versions'),
                (dut_image_versions, self.dut_image_versions, 'dut_image_versions'),
            ]
            for output, saved, name in comparisons:
                if not saved:
                    saved.update(output)
                elif len(output) == len(saved) and output != saved:
                    self.logger.info(f'CHANGED: [{name}] OLD {saved} -> NEW {output}')
                    saved.clear()
                    saved.update(output)
                    changed = True
        # If all the build numbers were the same we will only have one
        # entry in the set
        if len(self.non_vmanage_versions) > 1:
            # Log a warning if there is a version mismatch
            msg = 'WARNING: Version mismatch in non-vmanage devices. %s' % (self.non_vmanage_versions)
            self.logger.warning(msg)
            self.warnings_list.append(msg)
        if len(self.vmanage_versions) > 1:
            # Log a warning if there is a version mismatch
            msg = 'WARNING: Version mismatch in vmanage devices. %s' % (self.vmanage_versions)
            self.logger.warning(msg)
            self.warnings_list.append(msg)

        if has_any_error:
            self.logger.warning(
                "check_versions() encountered error(s), hence returning changed=False to prevent potential DB updates"
            )
            changed = False
        return changed

    def init_dt_dash(self):
        modules_dict = {}
        interfaces_dict = {}
        self.dtdash_dict = {}
        for machine in self.sessions['confd']:
            if self.tb.is_highrise(machine) or self.tb.is_xe_mode(machine):
                continue
            try:
                if machine.startswith('pm'):
                    if self.tb.is_cedge(machine):
                        modules_list = self.confd.get_hw_cedge_modules(machine, False)
                        if modules_list:
                            modules_dict[machine] = modules_list
                        interfaces_dict[machine] = self.confd.get_hw_cedge_interface_details(machine, False)
                    else:
                        modules_list = self.confd.get_hw_vedge_modules(machine, False)
                        if modules_list:
                            modules_dict[machine] = modules_list
                        interfaces_dict[machine] = self.confd.get_hw_vedge_interface_details(machine, False)
            except Exception:
                self.logger.warning("Failed to get data for {}".format(machine), exc_info=True)

        self.dtdash_dict['nodes'] = self.node_info
        self.dtdash_dict['modules'] = modules_dict
        self.dtdash_dict['interfaces'] = interfaces_dict
        self.save_dt_dash()

        if self.db_write and self.db_build_id:
            try:
                with self.get_db_client() as db_handle:
                    db_handle.push_node_info_to_db(self.db_build_id, self.node_info)
                    db_handle.push_modules_to_db(self.db_build_id, modules_dict)
                    db_handle.push_interfaces_to_db(self.db_build_id, interfaces_dict)
            except Exception:
                self.logger.warning("Error inserting data to regressdb", exc_info=True)

    def save_dt_dash(self):
        try:
            with open(os.path.join(self.logs_sub_dir, "dtdash.json"), 'w+') as dtdash_json_file:
                json_string = json.dumps(self.dtdash_dict)
                dtdash_json_file.write(json_string)
        except Exception:
            self.logger.warning("Error saving json to file", exc_info=True)

    def configure_machines_etc(self):
        for machine in self.sessions['confd']:
            # If the enable_short_rekey flag is set, change the ipsec rekey timer to 60s
            if self.enable_short_rekey is True and not self.image_type_is_vsmart(machine):
                res = self.confd.config_ipsec_rekey_timer(machine, 60)
                if res[0] is False:
                    self.logger.warning('WARNING: Could not set rekey timer to 60s on %s' % machine)
        if self.tls:
            for machine in self.tb.machines():
                if self.tb.image_type_is_vsmart(machine):
                    self.confd.config_security_tls(machine)
        if self.runner_systb is None:
            if self.nrcc is False:

                def route_consistency_check(machine):
                    if (
                        self.tb.is_nfvis(machine)
                        or (self.tb.image_type_is_vsmart(machine))
                        or (self.tb.is_ucs(machine))
                        or self.tb.is_highrise(machine)
                        or self.tb.is_xe_mode(machine)
                    ):
                        return
                    self.confd.config_rcc(machine)

                self.logger.info('\nEnabling route-consistency check on nodes')
                threads = []
                for machine in self.tb.machines():
                    if self.tb.is_highrise(machine) or self.tb.is_xe_mode(machine):
                        continue
                    t = Thread(target=route_consistency_check, args=(machine,))
                    t.start()
                    threads.append(t)
                for t in threads:
                    t.join()

        # Save the state of the testbed at the start of the suite, this will be useful for the back_to_base function
        # for machine in tb.machines():
        #     tb.call(machine, 'rm blank_config', root = True)
        # self.save_configs(config_name = 'blank_config', confd = confd)
        '''
        res = confd.save_config(machine, 'blank_config')
        if not res[0]:
            self.logger.warning('%s: %s' % (machine, res[1]))
        '''

    def call_runner_helper(self, progress="run"):
        if os.path.isfile(str(Paths().tools('scheduler/runnerHelper.js'))):
            try:
                process = subprocess.Popen(
                    ["node", "runnerHelper.js", str(self.db_build_id), progress],
                    cwd=str(Paths().tools("scheduler/")) + os.sep,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                process.wait()
            except Exception:
                pass
        else:
            self.logger.debug('Could not find file runnerHelper.js')

    def parse_upgrade_ttf(self):
        '''
        Parses the testcase names from the specified ttf.
        Returns the corresponding function objects as a list.
        '''
        path = str(Paths().scripts('test_tb_sw_upgrade_compact.ttf'))
        with open(path, 'r') as f:
            file_content = f.read()

        lines = [line for line in file_content.split('\n') if not line.startswith('#') and line.strip() != '']
        text = '\n'.join(lines)
        pattern = re.compile(re.escape(self.upgrade_module)+r"\s*-\s*(test_[a-zA-Z0-9_]+)\s*=\s*\[(.*)\]")
        matches = re.findall(pattern, text)
        m = import_module(self.upgrade_module)
        testcases = []
        for match in matches:
            fn, tags = m.__dict__[match[0]], [x.strip("' ") for x in match[1].split(',')]
            fn.tags = tags
            if self.upgrade_tag in tags:
                testcases.append(fn)
        return testcases

    def get_tags(self, suite, is_sanity):
        def check_configs(is_sanity):
            if is_sanity or self.args.skip_legacy:
                return False
            tags = self.args.tags_range or self.args.tags
            # If no tags are specified then check for left over configs after tests
            return bool(not tags or ('setup' in tags and 'cleanup' in tags))

        return (
            check_configs(is_sanity),
            [] if is_sanity else self.args.exclude_tags,
            '' if is_sanity else self.args.prepend_subtests,
            '' if is_sanity else self.args.append_subtests,
            [] if is_sanity else self.args.tags_range,
            [] if is_sanity else ([] if self.args.tags_range else self.get_all_tags(self.args.tags, suite)),
        )

    def is_setup_cleanup(self, func_tags):
        if not func_tags:
            return False
        return 'setup' in func_tags or 'cleanup' in func_tags

    def check_func_tags(self, func_tags, tags, exclude_tags, setup_cleanup):
        if not func_tags:
            return
        # There is no way to override the exclude_sim or exclude_hardware tag at run time
        # These tags mean the testbed is incapable of running the specified tests, regardless of how much
        # you want to run the tests
        # If this is a hardware testbed and exclude_hardware is in the tags then don't run this function
        # CHANGE: consider removing this, we don't need it anymore
        if 'nat' in func_tags and self.no_nat:
            raise SkippedTCException("Skipped since self.no_nat == True")
        elif ('exclude_allhw' in func_tags) and (self.tb.is_allhw_testbed()):
            raise SkippedTCException("Skipped.'exclude_allhw' in tags")
        elif 'exclude_mix' in func_tags and self.tb.hw and (not self.tb.is_allhw_testbed()):
            raise SkippedTCException("Skipped. 'exclude_mix' in tags")
        elif ('exclude_hardware' in func_tags) and (self.tb.hw):
            raise SkippedTCException("('exclude_hardware' in func_tags) and (self.tb.hw == True)")
        elif ('exclude_sim' in func_tags) and (self.tb.hw is False):
            raise SkippedTCException("('exclude_sim' in func_tags) and (self.tb.hw is False)")
        elif ('exclude_darwin' in func_tags) and self.tb.os_type == 'Darwin':
            raise SkippedTCException("('exclude_darwin' in func_tags) and self.tb.os_type == 'Darwin'")
        elif ('not_dpi' in func_tags) and (self.dpi):
            raise SkippedTCException("('not_dpi' in func_tags) and (self.dpi == True)")
        elif ('not_cellular' in func_tags) and (self.cellular):
            raise SkippedTCException("('not_cellular' in func_tags) and (self.cellular == True)")
        elif ('not_aws' in func_tags) and (self.tb.is_aws()):
            raise SkippedTCException("('not_aws' in func_tags) and (self.tb.is_aws() == True)")
        elif ('exclude_single_tloc' in func_tags) and (self.ultimate['api'].is_multi_tloc_set() is False):
            raise SkippedTCException(
                "('exclude_single_tloc' in func_tags) and (self.ultimate['api'].is_multi_tloc_set() is False)"
            )
        elif ('exclude_multi_tloc' in func_tags) and (self.ultimate['api'].is_multi_tloc_set()):
            raise SkippedTCException(
                "('exclude_multi_tloc' in func_tags) and (self.ultimate['api'].is_multi_tloc_set())"
            )
        elif ('exclude_ipv6' in func_tags) and (self.trans_ipv6 or self.ipv6):
            raise SkippedTCException("('exclude_ipv6' in func_tags) and ( self.trans_ipv6 or self.ipv6)")
        elif ('exclude_ipv6ra' in func_tags) and (self.ipv6_ra or self.ipv6):
            raise SkippedTCException("('exclude_ipv6ra' in func_tags) and (self.ipv6_ra or self.ipv6)")
        elif ('exclude_serv_ipv6' in func_tags) and (self.serv_ipv6 or self.ipv6):
            raise SkippedTCException("('exclude_serv_ipv6' in func_tags) and (self.serv_ipv6 or self.ipv6)")
        elif ('exclude_ipv4' in func_tags) and not self.trans_ipv6 and not self.ipv6_ra:
            raise SkippedTCException("('exclude_ipv4' in func_tags) and not self.trans_ipv6 and not self.ipv6_ra")
        elif ('exclude_tls' in func_tags) and (self.tls):
            raise SkippedTCException("('exclude_tls' in func_tags) and (self.tls)")
        elif ('spirent' in func_tags) and (
            self.ss is None or self.tb.spirent_configured() is None or self.ss.stc is None
        ):
            raise SkippedTCException(
                "('spirent' in func_tags) and (self.ss is None or self.tb.spirent_configured() is None or self.ss.stc is None)"
            )
        elif ('ixia' in func_tags) and (self.ixias is None):
            raise SkippedTCException("('ixia' in func_tags) and (self.ixias is None)")
        elif ('trex' in func_tags) and (self.trex is None):
            raise SkippedTCException("('trex' in func_tags) and (self.trex is None)")
        elif ('trex_stl' in func_tags) and (self.trex_stl is None):
            raise SkippedTCException("('trex_stl' in func_tags) and (self.trex_stl is None)")
        elif ('trex_stf' in func_tags) and (self.trex_stf is None):
            raise SkippedTCException("('trex_stf' in func_tags) and (self.trex_stf is None)")
        elif ('pagent' in func_tags) and (self.pagent is None):
            raise SkippedTCException("('pagent' in func_tags) and (self.pagent is None)")
        elif len(set(exclude_tags).intersection(set(func_tags))) != 0:
            raise SkippedTCException("len(set(exclude_tags).intersection(set(func_tags))) != 0")
        elif setup_cleanup is False and self.check_func_level(func_tags) is False:
            raise SkippedTCException("setup_cleanup is False and self.check_func_level(func_tags) == False")
        elif ('vmanage' in func_tags) and (self.include_vmanage is False) and (self.suite != 'vmanage_sdwan'):
            raise SkippedTCException(
                "('vmanage' in func_tags) and (self.include_vmanage is False) and (self.suite != 'vmanage_sdwan')"
            )
        elif ('exclude_for_pppoe' in func_tags) and (self.ultimate['ppp']):
            raise SkippedTCException("('exclude_for_pppoe' in func_tags) and (self.ultimate['ppp'] == True)")
        elif ('exclude_vedge' in func_tags) and (self.tb.is_cedge_testbed() is False):
            raise SkippedTCException("('exclude_vedge' in func_tags) and (self.tb.is_cedge_testbed() is False)")
        elif ('exclude_cedge' in func_tags) and (self.tb.is_cedge_testbed()):
            raise SkippedTCException("('exclude_cedge' in func_tags) and (self.tb.is_cedge_testbed() == True)")
        elif ('exclude_transport' in func_tags) and self.transport:
            raise SkippedTCException("('exclude_transport' in func_tags) and self.transport")
        elif ('exclude_service' in func_tags) and not self.transport:
            raise SkippedTCException("('exclude_service' in func_tags) and not self.transport")
        elif ('exclude_ikev1' in func_tags) and self.ikev1_aggressive:
            raise SkippedTCException("('exclude_ikev1' in func_tags) and self.ikev1_aggressive")
        elif ('exclude_ikev2' in func_tags) and self.ikev2:
            raise SkippedTCException("('exclude_ikev2' in func_tags) and self.ikev2")
        elif ('exclude_non_rest' in func_tags) and not self.restapi:
            raise SkippedTCException("('exclude_non_rest' in func_tags) and not self.restapi")
        elif (
            (
                'gw_utd' in func_tags
                or 'gw_ips' in func_tags
                or 'gw_ids' in func_tags
                or 'gw_urlf' in func_tags
                or 'gw_amp' in func_tags
            )
            and (self.tb.hw)
            and self.check_utd_ssl_support('utd')
        ):
            raise SkippedTCException("(self.tb.hw) and self.check_utd_ssl_support('utd')")
        elif ('gw_ssl' in func_tags) and (self.tb.hw) and self.check_utd_ssl_support('ssl'):
            raise SkippedTCException("('gw_ssl' in func_tags) and (self.tb.hw) and self.check_utd_ssl_support('ssl')")
        elif 'sdwan-init-et' in func_tags and self.tb.is_cloud_init():
            raise SkippedTCException("'sdwan-init-et' in func_tags and 'is_cloud_init' is true")
        elif len(tags) > 0:
            if self.upgrade_test:
                matching_tags = set(tags + [self.upgrade_tag]).intersection(func_tags)
            else:
                matching_tags = set(tags).intersection(func_tags)
            if not matching_tags:
                raise SkippedTCException("Tags selected by user {} do not match TC tags {}".format(tags, func_tags))
        elif 'exclude' in func_tags or 'fail' in func_tags:
            raise SkippedTCException("'exclude' in func_tags or 'fail' in func_tags")
        # If this function has the 'break' tag then stop the script (after the test has been run)
        # This is mainly for testers
        # Use this tag to run a subset of tests without having to change the tags for multiple tests
        if 'break' in func_tags:
            raise BlockedTCException("TC has break tag")

    # Make the testcase execution "for" loop as an inner function so that we can run it twice.
    # First iteration to get the total testcases count and second to actually execute the testcases.
    def run_script_inner_function(
        self,
        script,
        is_sanity,
        ordered_func,
        prepend_subtests,
        append_subtests,
        tags,
        exclude_tags,
        execute_tests=False,
    ):
        self.number_of_test_cases = 0
        self.testcase_fail_count = 0
        test_case_tracker = {}
        # For each function/test case, deal with the tags and then run the test if needed
        tc_blocked = False
        # Aggregated result of all test cases.
        # 0 - RETVAL_SUCCESS, -1 - RETVAL_OTHER, 1 - RETVAL_FAILURE or RETVAL_ERRORED
        result = 0
        for func in ordered_func:
            item = func.name
            if execute_tests:
                self.summary.set_testcase_src_file_path(
                    self.test_suites[script], item, self.tc_src_code_logger.get_tc_src_file_path(func)
                )

            start_time_int = time.time()
            start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
            if not execute_tests:
                self.results.total_tests += 1
            res = 0
            if self.upgrade_test:
                if not {'setup', 'cleanup', self.upgrade_tag}.intersection(set(func.tags)):
                    if item not in test_case_tracker:
                        test_case_tracker[item] = 1
                        item += '_1'
                    else:
                        test_case_tracker[item] += 1
                        item += '_' + str(test_case_tracker[item])

            tc_result = TCResult.NOT_RUN
            test_case_name = "{}-{}".format(self.db_test_suite, func.name)
            # init the tc state and name
            misc.cur_testcase.set_tc_state(state=True, case=test_case_name, step="", forced=True)

            if self.db_write and self.db_build_id and not execute_tests:
                try:
                    tc_info = [
                        self.db_build_id,
                        self.db_build,
                        self.tb_hostname,
                        self.db_suite,
                        test_case_name,
                        tc_result,  # Index of tc_results should match TEST_INFO_INDEX_OF_TC_RESULT
                        '0:00:00',
                        '',
                        self.db_tb_name,
                        '',
                        '',
                        'NOT_RUN',
                    ]
                    self._tcs_summary[test_case_name] = tc_info
                    with self.get_db_client() as db_handle:
                        db_handle.push_test_to_db(*tc_info)
                except Exception:
                    self.logger.warning(
                        "Exception while inserting data for TC {}".format(test_case_name), exc_info=True
                    )
            try:
                if func.supported_versions and self.db_build:
                    # if dut is cedge (17.x) we need 20.x version to compare
                    normalized_builds = normalize_builds(self.db_build)
                    if not any([b in func.supported_versions for b in normalized_builds if b]):
                        if not execute_tests:  # method is called twice, this prevents double logging
                            self.logger.warning(
                                "Non of normalized DUT build version(s) '{}' within testcase conditions: '{}', "
                                "testcase '{}' will be skipped".format(
                                    normalized_builds, func.supported_versions, func.name
                                )
                            )
                            self.results.version_skipped.append(func.name)
                        raise SkippedTCException(
                            "Skipped, DUT version: {} test is defined for {}".format(
                                self.db_build, func.supported_versions
                            )
                        )
                    else:
                        if not execute_tests:  # method is called twice, this prevents double logging
                            self.logger.info(
                                "One or more normalized DUT build version '{}' within testcase conditions: '{}', "
                                "testcase '{}' will be executed".format(
                                    normalized_builds, func.supported_versions, func.name
                                )
                            )

                func_tags = set(func.tags)
                func_tags.add(item)
                setup_cleanup = self.is_setup_cleanup(func_tags)
                self.check_func_tags(func_tags, tags, exclude_tags, setup_cleanup)
            except SkippedTCException as ex:
                self.logger.debug("Skipped: {}. {}".format(item, ex))
                tc_result = TCResult.SKIPPED
                continue
            except BlockedTCException:
                tc_blocked = True
                tc_result = TCResult.BLOCKED
                continue
            except TimeoutTCException:
                tc_result = TCResult.TIMEDOUT
                self.logger.exception("")
                continue
            except Exception:
                tc_result = TCResult.ERRORED
                self.logger.exception("")
                continue
            except SystemExit:
                # Mark as errored so user will see state updated in DB/regressDB
                tc_result = TCResult.ERRORED
                self.logger.exception("")
                # raise as user intention was to stop suite execution
                raise
            finally:
                tc_runtime = int(time.time() - start_time_int)
                end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
                self.db_test_duration = str(datetime.timedelta(seconds=tc_runtime))
                tc_result, _ = self.override_tc_result_based_on_func_tags(tc_result, RETVAL_SUCCESS, func, func_tags)
                self.summary.set_testcase_time(self.test_suites[script], item, tc_runtime)
                self.summary.set_testcase_start_time(self.test_suites[script], item, start_time_str)
                self.summary.set_testcase_end_time(self.test_suites[script], item, end_time_str)
                if not execute_tests:
                    self.summary.set_testcase_result(self.test_suites[script], item, TCResult.to_xml(TCResult.BLOCKED))
                elif tc_result in {TCResult.SKIPPED, TCResult.BLOCKED, TCResult.ERRORED, TCResult.TIMEDOUT}:
                    self.results.add_result(tc_result)
                    self.summary.set_testcase_result(self.test_suites[script], item, TCResult.to_xml(tc_result))

                    if self.db_write and self.db_build_id:
                        try:
                            tc_info = [
                                self.db_build_id,
                                self.db_build,
                                self.tb_hostname,
                                self.db_suite,
                                test_case_name,
                                tc_result,  # Index of tc_results should match TEST_INFO_INDEX_OF_TC_RESULT
                                self.db_test_duration,
                                '',
                                self.db_tb_name,
                                start_time_str,
                                end_time_str,
                                'NOT_RUN',
                            ]
                            self._tcs_summary[test_case_name] = tc_info
                            with self.get_db_client() as db_handle:
                                db_handle.update_tc_state(*tc_info)
                        except Exception:
                            self._tcs_update_errors.add(test_case_name)
                            self.logger.warning(
                                "Exception while updating data for TC {}".format(test_case_name), exc_info=True
                            )

            # If TC has tags and none of the conditions listed above were met, or TC didn't have any tags then TC subtests will run below
            self.number_of_test_cases += 1
            if not execute_tests:
                res = -5
                self.logger.debug('%3d\tName: %s' % (self.number_of_test_cases, item))
            else:
                try:
                    self.tc_src_code_logger.mark_tc_start(func)
                    # no need to run if TC is blocked
                    if tc_blocked:
                        raise BlockedTCException("")

                    for session in self.session_wrappers():
                        self.logger.debug("%s.start_tc(%r)", session.__class__.__name__, item)
                        session.start_tc(item)
                    func.module = self.args.modules.get_suite_module(func.module_name)
                    subtests = Executioner(testcase=func, skip_summary=True, subtest_type_validation=False).tests

                    # DEBUG CALLBACK
                    # Mark The Running Testcases Function

                    # Mark the running testcase object for Later lookup by functions which need
                    # information about currently executed testcase
                    # type : ttf_parser.TestCase
                    self.current_running_testcase = func

                    if self.subtest_casting_is_needed(subtests):
                        old_subtests = subtests
                        subtests = [subtests]
                        self.logger.warning(
                            "Subtests spec casting occurred for %s: %r => %r. Check if code is correct!",
                            func.function,
                            old_subtests,
                            subtests,
                        )

                    if not subtests or not isinstance(subtests, list):
                        raise SkippedTCException("{} is marked as 'SKIPPED'. TC returns an empty list".format(item))

                    invalid_subtests = []
                    for subtest in subtests:
                        violation = misc.get_subtest_structure_violation(subtest)
                        if not violation:
                            continue
                        message = "\t[SUBTEST ERROR] '{: <40}'\t{}".format(repr(subtest)[:40], violation)
                        invalid_subtests.append(message)

                    if invalid_subtests:
                        subtests_str = "\n".join(invalid_subtests)
                        template = "{} has errors and is likely to fail! Following subtests are malformed:\n{}"
                        self.logger.error(template.format(item, subtests_str))

                    subtests_to_run = prepend_subtests + subtests + append_subtests
                    if self.log_running_config:
                        if not setup_cleanup and not self.setup_done and not is_sanity:
                            self.setup_done = True
                            self.logger.info("saving config-after-setup")
                            self.get_all_configs(file_name='config-after-setup')
                        elif setup_cleanup and not self.tests_done and self.setup_done and not is_sanity:
                            self.tests_done = True
                            self.logger.info("saving config-before-cleanup")
                            self.get_all_configs(file_name='config-before-cleanup')
                    # percentage = (WIDTH * 1.0)/len(ordered_func)
                    percentage = 0
                    with self.profiler.run_testcase(func.name):
                        SmartDebug.set_subtests_to_run(ordered_func, func, subtests_to_run)
                        res = self.execute(subtests_to_run, func, percentage, True)
                    # TODO: Understand why we execute first and mark as skipped later.
                    # We have all data needed to skip without attempting to execute.
                    self.skip_due_to_subtests_structure(item, subtests)
                    if res < 0:
                        # stoponfail mode, block subsequent testcases
                        tc_blocked = True
                except KeyboardInterrupt:
                    tc_result = TCResult.ABORTED
                    res = RETVAL_OTHER
                    self.summary.set_testcase_text(self.test_suites[script], item, "Received keyboard interrupt")
                    # TODO: should we abort all subsequent tests (same as in 'break' tag)?
                except SkippedTCException as ex:
                    tc_result = TCResult.SKIPPED
                    self.logger.warning(ex)
                except BlockedTCException:
                    tc_result = TCResult.BLOCKED
                except TimeoutTCException:
                    tc_result = TCResult.TIMEDOUT
                except SystemExit:
                    # Mark as errored so user will see state updated in DB/regressDB
                    tc_result = TCResult.ERRORED
                    # raise as user intention was to stop suite execution
                    raise
                except Exception as ex:
                    tc_result = TCResult.BLOCKED if tc_blocked else TCResult.ERRORED
                    res = RETVAL_OTHER
                    self.logger.exception(
                        "Exception during test step collection for test case {}".format(test_case_name)
                    )
                    self.summary.set_testcase_text(self.test_suites[script], item, str(ex))
                else:
                    if res == RETVAL_SUCCESS:
                        tc_result = TCResult.PASS
                    elif res == RETVAL_ERRORED:
                        tc_result = TCResult.ERRORED
                    else:
                        tc_result = TCResult.FAIL
                finally:
                    tc_result, res = self.override_tc_result_based_on_func_tags(tc_result, res, func, func_tags)
                    self.results.add_result(tc_result)

                    if tc_result in {TCResult.FAIL, TCResult.ABORTED, TCResult.ERRORED, TCResult.TIMEDOUT}:
                        self.db_test_suite_result = 'FAIL'

                    if self.db_write and self.db_build_id:
                        # Trigger bugbuddy at testcase level
                        # do not trigger if TC got timeout
                        if tc_result in {TCResult.FAIL, TCResult.ERRORED} and not self.quick:
                            # Run Defect Companion only for N number of failures.
                            run_component_finder = False
                            if self.testcase_fail_count < 1:
                                run_component_finder = True
                            try:
                                self.bugbuddy_util.run_bugbuddy(
                                    func.name,
                                    self.suite_name,
                                    None,
                                    self.logs_sub_dir,
                                    self.db_build,
                                    self.components,
                                    self.logger,
                                    self.db_url,
                                    run_component_finder,
                                )

                            except Exception as e:
                                self.logger.warning(
                                    "Bug Buddy logs collection failed for {} with error: {}".format(func.name, e)
                                )
                            self.testcase_fail_count += 1
                        bugbuddy_result = self.bugbuddy_util.get_run_status(func.name)
                        self.logger.debug("Bug Buddy result for tc {} is : {}".format(func.name, bugbuddy_result))

                    tc_runtime = int(time.time() - start_time_int)
                    self.db_test_duration = str(datetime.timedelta(seconds=tc_runtime))
                    end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())

                    self.summary.set_testcase_time(self.test_suites[script], item, tc_runtime)
                    self.summary.set_testcase_start_time(self.test_suites[script], item, start_time_str)
                    self.summary.set_testcase_end_time(self.test_suites[script], item, end_time_str)
                    self.summary.set_testcase_result(self.test_suites[script], item, TCResult.to_xml(tc_result))
                    self.summary.set_testcase_module(self.test_suites[script], func.module_name, item)

                    if self.db_write and self.db_build_id:
                        try:
                            tc_info = [
                                self.db_build_id,
                                self.db_build,
                                self.tb_hostname,
                                self.db_suite,
                                test_case_name,
                                tc_result,  # Index of tc_results should match TEST_INFO_INDEX_OF_TC_RESULT
                                self.db_test_duration,
                                '',
                                self.db_tb_name,
                                start_time_str,
                                end_time_str,
                                bugbuddy_result,
                            ]
                            self._tcs_summary[test_case_name] = tc_info
                            with self.get_db_client() as db_handle:
                                bug_id = db_handle.fetch_bug_id(test_case_name, self.db_suite)
                                if bug_id is None:
                                    bug_id = ''
                                tc_info[TEST_INFO_INDEX_OF_BUG_ID] = bug_id
                                self._tcs_summary[test_case_name] = tc_info
                                db_handle.update_tc_state(*tc_info)
                        except Exception:
                            self._tcs_update_errors.add(test_case_name)
                            self.logger.warning(
                                "Exception while updating data for TC {}".format(test_case_name), exc_info=True
                            )
                    self.tc_src_code_logger.mark_tc_end(func)

            # If the reteval of the executed function was -1 then set the result variable to the same value and stop running tests
            # We use the result variable, later on in the script, to figure out if there were any failures or not
            if res == RETVAL_OTHER:
                result = -1
                if setup_cleanup and self.stop_on_setup_fail:
                    tc_blocked = True
                    (check_configs, exclude_tags, prepend_tag, append_tag, tags_range, tags) = self.get_tags(
                        self.suite, is_sanity
                    )
                    if check_configs:
                        self.logger.info("+" * 10, setup_cleanup, check_configs, "+" * 10)
                        self.logger.info(f"res: {res}")
                elif self.first_fail:
                    tc_blocked = True
            # Else just set result to False
            elif res == RETVAL_FAILURE or res == RETVAL_ERRORED:
                result = 1
                # If one of the setup/cleanup test cases fails then simply go back to the base config
                if setup_cleanup and self.stop_on_setup_fail:
                    if self.no_cleanup_setup_failure:
                        ret = 1
                    else:
                        ret = self.back_to_base()
                    self.errors_list.append(self.print_line())
                    self.errors_list.append('%s FAILED' % self.suite)
                    self.errors_list.append(self.print_line())
                    if ret == 1:
                        result = -1
                    tc_blocked = True
                elif self.first_fail:
                    tc_blocked = True
        if not execute_tests:
            return self.number_of_test_cases
        else:
            return result

    def run_script(self, script_path):
        """
        Parse the script and execute all the tests
        """
        # In this function the terms 'function' and 'test case' are used interchangeably
        if self.generate_configs:
            #Set the tags to only 'setup'
            #Then we do a setup for the specified suite and get the configs at that point
            tags = ['setup']
        self.progress_bar_count = 0.0
        self.number_of_tests = 0
        self.number_of_failed_tests = 0
        self.number_of_subtests = 0
        self.failed_subtests = 0
        #Get the current time so we can figure out the total time it takes for the script to execute
        start = time.time()
        module_dir = os.path.dirname(script_path)
        if len(module_dir) != 0:
            if not os.path.isdir(module_dir):
                self.logger.error(self.error('Could not find dir ' + module_dir))
                return 1
        script = os.path.basename(script_path).split('.')[0]
        self.current_suite_name = script
        self.test_suites[script] = self.summary.register_test_suite(script, "fail")

        ordered_func = []
        upgrade_fns = []
        setup = None
        cleanup = None

        is_sanity = os.path.basename(script_path) == 'test_sanity.ttf'
        (check_configs, exclude_tags, prepend_tag, append_tag, tags_range, tags) = self.get_tags(self.suite, is_sanity)
        if check_configs:
            if self.log_running_config and not self.before_setup and not is_sanity:
                self.logger.info("saving config-before-setup")
                self.before_setup = True
                run_configs = self.get_all_configs(file_name='config-before-setup')
            else:
                run_configs = self.get_all_configs()

        #Search for any modules that need to be imported
        #These modules need to be defined in the script
        modules = [m.name for m in self.args.modules.loaded_modules]
        if not self.args.ttf.modules:
            self.logger.error('No modules definition found in %s' % script_path)
            return 1

        #Parse tile, and store them in a list
        modules_dict = {}
        if self.upgrade_test:
            upgrade_fns = self.parse_upgrade_ttf()
            modules.append(self.upgrade_module)

        # Save module lists info
        no_merged_modules = modules[:]

        for module in self.debug_callback.testcases_callback["callback_module_list"]:
            if module not in modules:
                modules.append(module)

        # see tests/lib/suitemodules.py
        self.args.modules.set_contexts(self.args)

        #Go through the list of modules and import each one of them
        for module in modules:
            if module.startswith('cases'):
                # no suites in tests/scripts/cases use ultimate
                continue
            # import_module() here is redundant, as all modules are already imported
            # by common_runner.init() . However, refactor is being done in stages.
            modules_dict[module] = import_module(module)
            # Call the get_ultimate and set_globals functions
            # Every script must define these two functions
            # The get_ultimate function passes the ultimate dictionary to the script
            # The set_globals function is used to set any global variables you want for the script
            try:
                if hasattr(modules_dict[module], 'get_ultimate') and not self.args.skip_legacy:
                    self.logger.debug(f'calling {module}.get_ultimate()')
                    modules_dict[module].get_ultimate(self.ultimate)
                if hasattr(modules_dict[module], 'set_globals') and not self.args.skip_legacy:
                    self.logger.debug(f'calling {module}.set_globals()')
                    start = timeit.default_timer()
                    modules_dict[module].set_globals()
                    diff = timeit.default_timer() - start
                    msg = '%s.set_globals() took %.1f secs'
                    if diff > 5.0:
                        self.logger.warning(msg, module, diff)
                    else:
                        self.logger.info(msg, module, diff)

                self.debug_callback.process(modules_dict, module)

            except AttributeError as e:
                # DEBUG CALLBCK
                if module not in no_merged_modules:
                    self.logger.error("Error From Callback Module: {}".format(module))
                self.logger.error('%s: %s' % (module, repr(e)), exc_info=True)
                return 1

        vmanages = [m for m in self.tb.machines() if self.tb.personality(m) == "vmanage"]
        if not self.args.skip_legacy:
            self.tb.testbed_vmanage_master_cert_creation(vmanages)

        i = 0
        for test_case in self.args.ttf.test_cases:
            if script_path != str(test_case.ttfile):
                continue
            # run_script: Add actual function to TestDefinition
            self.bind_testcase(test_case, script_path)

            if tags_range is not None and i < len(tags_range):
                #We need to get the indexes of the first and last test cases in the range
                if tags_range[i][0] == test_case.name:
                    tags_range[i][0] = len(ordered_func)
                if tags_range[i][1] == test_case.name:
                    tags_range[i][1] = len(ordered_func)
                    i += 1

            self.debug_callback.set_callback(test_case)

            #If the script is not sanity execute the following code
            #We dont need to execute this code for sanity since this is tag specific code and sanity does not have any tags
            if not is_sanity:
                # Figure out which functions are setup functions and which are cleanup functions
                # We need this information for random runs becuase even in random runs the setup and cleanup have to be done in the original order
                # We make the assumption that all the setup functions are declared first with no non-setup functions between them
                # We make the same assumption for the cleanup functions except for the fact that they are declared at the end
                # Keep going if the function is 'exclude' or 'fail'
                if 'exclude' not in test_case.tags and 'fail' not in test_case.tags:
                    if setup is None:
                        if 'setup' not in test_case.tags:
                            setup = len(ordered_func)
                    if cleanup is None:
                        if 'cleanup' in test_case.tags:
                            cleanup = len(ordered_func)
            #Add this function to the ordered list of functions
            ordered_func.append(test_case)
        # rename test cases with same name by appending index to name
        testcase_names = Counter([(testcase.module_name, testcase.name) for testcase in self.args.ttf.test_cases])
        duplicate_names = {
            (module_name, test_case_name): 0
            for (module_name, test_case_name), count in testcase_names.items()
            if count > 1
        }
        for testcase in self.args.ttf.test_cases:
            if (testcase.module_name, testcase.name) in duplicate_names:
                self.logger.info(
                    "Test case name {} is duplicated in module {}, renaming it to avoid conflicts".format(
                        testcase.name, testcase.module_name
                    )
                )
                duplicate_names[(testcase.module_name, testcase.name)] += 1
                testcase.name = f"{testcase.name}_{duplicate_names[(testcase.module_name, testcase.name)]}"
                self.logger.info("Renamed test case to {}".format(testcase.name))
                # Create function for name with index, e.g. test_func_2 for test_func if there are 2 test cases with the same name
                module = import_module(testcase.module_name)
                setattr(module, testcase.name, testcase.function)

        #If the prompt flag was specified
        if self.prompt:
            #Set variables to make the prompt mode exprience more user friendly
            for module in modules_dict:
                exec('%s = modules_dict["%s"]' % (module, module), globals(), locals())
            for entry in self.ultimate:
                exec('%s = self.ultimate["%s"]' % (entry, entry), locals(), locals())
            cmds = list(modules_dict.keys()) + list(self.ultimate.keys())
            #Create a dictionary containing all the global and local variables from the runner and the script
            options = dict(list(globals().items()) + list(locals().items()))# + module.__dict__.items())
            try:
                #Start a python interactive prompt with access to the dictionary of all the variables
                code.interact(local = options, banner = 'To get a list of modules and session handles use "cmds"')
            except SystemExit:
                pass
            #If the user exits the interactive mode then return from this function
            return 0

        if self.db_write and self.db_build_id and self.db_build:
            try:
                with self.get_db_client() as db_handle:
                    self.logger.info("Updating build version in DB: Build version based on DUT OS: %s" % self.db_build)
                    db_handle.update_build_to_db(self.db_build_id, self.db_build, self.db_tb_name)
                    self.call_runner_helper()
            except Exception:
                self.logger.warning("Failed to update DB", exc_info=True)

        #Print the name of the script that we will execute
        self.logger.info(script.upper())
        if is_sanity is False:
            if self.load_configs:
                self.logger.info('Loading config files on to the nodes ...')
                res = self.load_all_configs(self.configs_dir_name)
                if res != 0:
                    return 1
                exclude_tags = ['setup'] + exclude_tags
        #Add the name of the script, that we will execute, to the list of errors so that we can break the errors in to sections
        #If there is no error in the script then we will simply remove the name of the script
        #Same goes for warnings
        self.errors_list.append(script.upper())
        self.warnings_list.append(script.upper())
        warn_list_len = len(self.warnings_list)
        result = 0
        #If the randomize flag has been specified and the script is not sanity randomize the order of the tests
        if not is_sanity:
            if tags_range is not None:
                new_ordered_func = []
                for index in range(i):
                    new_ordered_func += ordered_func[tags_range[index][0] : tags_range[index][1] + 1]
                ordered_func = new_ordered_func
            if self.randomize:
                #If there were no functions with the cleanup tag
                if cleanup is None:
                    cleanup = len(ordered_func)
                #Get all the functions that are not setup or cleanup functions
                temp = ordered_func[setup:cleanup]
                times = random.randint(1, 6)
                #Shuffle the tests
                for i in range(times):
                    random.shuffle(temp)
                # Update the ordered functions list to have the shuffled functions
                ordered_func = ordered_func[:setup] + temp + ordered_func[cleanup:]
            if self.upgrade_test:
                if cleanup is None:
                    cleanup = len(ordered_func)
                tests = ordered_func[setup:cleanup]
                ordered_func = ordered_func[:setup] + tests + upgrade_fns + tests + ordered_func[cleanup:]

        # Process prepend_tag. if tag does not exist, then returns a null list
        prepend_test = [x for x in ordered_func if x.name == prepend_tag]
        if len(prepend_test) == 1:
            prepend_subtests = prepend_test[0]()
        else:
            prepend_subtests = []

        #Process append_tag. if tag does not exist, then returns a null list
        append_test = [x for x in ordered_func if x.name == append_tag]
        if len(append_test) == 1:
            append_subtests = append_test[0]()
        else:
            append_subtests = []

        # Call the run_script_inner_function() first time to get the testcases count
        self.tests_in_suite = self.run_script_inner_function(
            script, is_sanity, ordered_func, prepend_subtests, append_subtests, tags, exclude_tags, execute_tests=False
        )
        self.logger.info('Total testcases to execute: %s' % self.tests_in_suite)
        # Call the run_script_inner_function() second time to execute the testcases
        result = self.run_script_inner_function(
            script, is_sanity, ordered_func, prepend_subtests, append_subtests, tags, exclude_tags, execute_tests=True
        )
        if check_configs:
            if not self.cleanup_done and self.log_running_config and not is_sanity:
                self.cleanup_done = True
                self.logger.info("saving config-after-cleanup")
                res = self.compare_configs(run_configs, file_name='config-after-cleanup')
            else:
                res = self.compare_configs(run_configs)
            for machine, diff in res:
                self.warnings_list.append('Config mismatch on %s' % machine)
                self.warnings_list.append(diff)

        #If there were no failures
        if result == 0:
            #Remove all the function names that we put in to the list of errors
            self.errors_list.remove(script.upper())
            #If the generate_configs flag was set then save configs for each machine and then copy them out
            if self.generate_configs:
                self.save_configs(self.configs_dir_name)
        if len(self.warnings_list) > warn_list_len:
            self.warnings_list.append(self.print_line(char = '='))
        else:
            self.warnings_list.remove(script.upper())
        self.print_verbose(count = WIDTH)

        if self.failed_subtests == 0 and not self.core_found:
            self.test_suites[script].set('result', 'pass')
        return result

    #Structure of a subtest: [function {machine: [arguments]}, result]
    def execute(self, subtests, testcase, percent=0, setup_cleanup=False):
        """Runs the subtests of the current test function"""
        name = testcase.name
        errors = []
        warnings = []
        retval = RETVAL_SUCCESS
        # It can happen that we have None here,
        # i.e. during runs with -pr option (aka interactive mode)
        if self.current_running_testcase is None:
            self.current_running_testcase = testcase

        self.summary.set_testcase_result(self.test_suites[self.current_suite_name], name, TCResult.NOT_RUN)
        test = self.summary.get_testcase_by_name(name)

        if self.randomly_restart_daemons:
            self.tb.restart_random_daemon()
        start_time = time.time()
        #Get the running config for every node after we are done with all the setup functions
        #We will use these configs later to make sure that every test/function cleans up after itself
        if setup_cleanup is False:
            run_configs = self.get_all_configs()
        if type(subtests) == list:
            if len(subtests) == 0:
                test.set('result', 'pass')
                return 0
            self.print_test_name_verbose(testcase.full_name_w_params)

            for mch in self.tb.machines():
                self.print_func_name_to_logs(mch, name, subtest=False)
            for machine in self.ultimate['sessions']['confd']:
                border = '\n\n' + '>' * 15 + ' Starting %s ' % name + '>' * 15 + '\n\n'
                try:
                    self.ultimate['sessions']['confd'][machine].logfile.write(border)
                except AttributeError:
                    pass
                except Exception:
                    self.logger.error(traceback.format_exc())
            for machine in self.ultimate['sessions']['iosxe']:
                border = '\n\n' + '>' * 15 + ' Starting %s ' % name + '>' * 15 + '\n\n'
                try:
                    self.ultimate['sessions']['iosxe'][machine].logfile.write(border)
                except AttributeError:
                    pass
                except Exception:
                    self.logger.error(traceback.format_exc())
            res = RETVAL_ERROR_DEFAULT
            try:
                res = self.process_subtests(subtests, 0, errors, test)
            except RuntimeError:
                self.logger.error(traceback.format_exc())
                self.spirent_failure = True  # How do you know RuntimeError is always Spirent?
                self.logger.error("Spirent RuntimeError. Stopping regression run.")
                res = RETVAL_ERROR_SPIRENT_RUNTIME
                raise
            except Exception:
                self.logger.error(traceback.format_exc())
                res = RETVAL_OTHER
                raise
            finally:
                if self.collect_memory:
                    for machine in self.get_dut_hosts(sanity_check=False):
                        if self.tb.is_cedge(machine):
                            self.tb.collect_memory_usage_from_cedge(machine, name)

                core_files_found = False
                if not self.quick:
                    self.logger.info("Checking core files after running subtests of {}".format(name))
                    dst = os.path.join(self.logs_sub_dir, 'core_files', name)
                    core_files_found = bool(self.check_core_files(warnings, dst))
                #self.errors_list = self.errors_list + errors
                if res != 0:
                    retval = res
                else:
                    if core_files_found:
                        # although test is PASS as res == 0 mark it as FAIL by returning negative value
                        retval = RETVAL_ERROR_ERROR_CORE_FILES_FOUND
                        errors.append("Core files found!")
                    else:
                        test.set('result', 'pass')
        elif subtests is None:
            pass
        else:
            self.logger.error(self.error('Incorrect parameters given to execute'))
        #We expect every test case to clean up after itself and leave the nodes in their original state,
        #the state they were in before the test started
        #This does not apply to test cases which are tagged as 'setup' or 'cleanup'
        warnings.append(self.print_line(char = '='))
        warnings.append('Warnings - %s' % name)
        warnings.append(self.print_line(char = '='))
        if setup_cleanup is False:
            res = self.compare_configs(run_configs)
            if res is not None:
                for machine, diff in res:
                    warnings.append('Config mismatch on %s' % machine)
                    warnings.append(diff)
        test_time = int(time.time() - start_time)
        #FIXME - set test case duration for db
        self.db_test_duration = str(datetime.timedelta(seconds=test_time))
        self.logger.info('Test time: %is' % test_time)
        if self.prompt != True:
            self.number_of_tests += 1
        if len(errors) > 0:
            header = [self.print_line(char = '*'), 'Errors - %s' % name, self.print_line(char = '*')]
            errors = header + errors
            self.number_of_failed_tests += 1

        monitor_results = self.tb.get_monitor_results()
        if monitor_results:
            warnings.append('[MachinesMonitor] CPU/MEM warnings')
            warnings.extend(monitor_results)
            warnings.append('\n')

        if len(warnings) > 3:
            self.log_warnings(warnings)
        self.log_errors(errors, False)
        if len(warnings) > 3:
            self.logger.warning(self.print_line(char = '='))
        return retval

    def process_subtests(self, subtests, val, errors, test):
        # type: (typing.List[vtyping.TestSteps], typing.Literal[0, 1, 2, 3], typing.List[str], typing.Any) -> typing.Literal[-1, 0, 1, 2]
        i = 0
        retval = RETVAL_SUCCESS
        group_tags = ['CASE', 'CHECK', 'GROUP']
        multi_proc_tags = ['PARALLEL', 'BLOCK']
        all_multi_proc_tags = ['PARALLEL', 'BLOCK', 'SET']
        #CASE: For all the subtests specified within this tag as long as one of them passes consider it an overall success (don't exit on -x) but log all the failures
        #CHECK: For all the subtests within this tag as long as any one of them passes consider this a success
        #GROUP: For all the subtests within this tag as long as they are passing keep going, if any one of them fails then skip all the rest of the tagged tests

        # DEBUG CALLBACK
        # Mark Testcase as Success
        subtest_fail = False
        tc_timeout_sec = TimeoutTCException.get_tout_val()

        tc = self.current_running_testcase
        tc_name = tc.name
        requested_tout_str = None
        look_for_tag = TimeoutTCException.look_for_tag
        for param, param_val in tc.tags_w_params.items():
            if look_for_tag == param:
                requested_tout_str = param_val
                break
        if requested_tout_str:
            ret, val_sec = TimeoutTCException.parse_str_val(requested_tout_str)
            if ret:
                tc_timeout_sec = val_sec
                self.logger.info(
                    "Using test case specific timeout [from TTF] value: {}".format(
                        TimeoutTCException.get_tout_val_human(tc_timeout_sec)
                    )
                )
            else:
                self.logger.warning(
                    "Problem with settig tescase timeout [from TTF] value of: {}".format(requested_tout_str)
                )
        tc_start = time.time()
        while i < len(subtests):
            if time.time() > tc_start + tc_timeout_sec:
                raise TimeoutTCException(
                    "Timeout of {} when executing {} testcase".format(
                        TimeoutTCException.get_tout_val_human(tc_timeout_sec), tc_name
                    )
                )
            mode = 0
            subtest_index = i
            subtest = subtests[i]
            if subtest in all_multi_proc_tags and self.ignore_parallel:
                i += 1
                continue
            if subtest in multi_proc_tags:
                end_tag = subtests[i + 1:].index(subtest) + i + 1
                self.results.parallel_subtests += calculate_parallel_subtests(subtests[i:end_tag])
                if subtest == 'PARALLEL':
                    subtest = ['STARTING PARALLEL TESTS'] + subtests[i + 1: end_tag]
                    verify_possible_parallel_subtests_collisions(self.logger, subtest)
                    subtests.insert(end_tag + 1, 'FINISHED PARALLEL TESTS')
                    mode = 1
                    if (end_tag - i) == 1:
                        self.logger.warning("Empty PARALLEL block encountered in subtests.")
                elif subtest == 'BLOCK':
                    subtest = subtests[i + 1: end_tag]
                    subtests.insert(end_tag + 1, 'FINISHED BLOCK TESTS')
                    k = 0
                    subtest_blocks = [['STARTING BLOCK TESTS']]
                    while k < len(subtest):
                        if subtest[k] != 'SET':
                            self.logger.error('SET tag mismatch')
                            return -1
                        else:
                            set_end_tags = subtest[k + 1:].index(subtest[k]) + k + 1
                            if (set_end_tags - k) == 1:
                                self.logger.warning("Empty SET block encountered in subtests.")
                            subtest_blocks += [subtest[k + 1: set_end_tags]]
                            k = set_end_tags + 1
                    verify_possible_parallel_block_subtests_collisions(
                        self.logger, self.machines_with_sessions, subtest_blocks
                    )
                    mode = 2
                    subtest_index += 1
                subtest_index += 1
                i = end_tag
            if subtest in group_tags:
                end_tag = subtests[i + 1:].index(subtest) + i + 1
                if subtest == 'CASE':
                    val = 1
                elif subtest == 'CHECK':
                    val = 2
                elif subtest == 'GROUP':
                    val = 3
                res = self.process_subtests(subtests[i + 1: end_tag], val, errors, test)
                if res > 0:
                    return res
                i = end_tag
            else:
                if type(subtest) == int:
                    self.print_verbose('%ss sleep' % subtest)
                    time.sleep(subtest)
                elif isinstance(subtest, (str, unicode)):
                    if subtest == 'interact':
                        if self.interactive:
                            try:
                                code.interact(local = dict(globals(), **locals()))
                            except SystemExit:
                                pass
                    else:
                        self.print_verbose(subtest)
                else:
                    p = []
                    q = multiprocessing.Queue()
                    if mode == 2:
                        subtest = []
                        for block in subtest_blocks:
                            proc = multiprocessing.Process(
                                target=self.run_subtest, args=(test, block, q, subtest_index, mode)
                            )
                            proc.start()
                            p.append(proc)
                            subtest_index += len(block) + 2
                            subtest += block
                    else:
                        p = self.run_subtest(test, subtest, q, subtest_index, mode)
                    # List of strings, each represents given subtest as string
                    # Used to keep track of what we put into the processing queue and what we get from the queue.
                    #
                    # Goal of having it is to know what was left in the queue in case of subtest timeout.
                    subtests_as_str = []
                    if mode == 0:
                        count = 1
                        subtests_as_str = [str([subtests])]
                    else:
                        count = len(subtest)
                        subtests_as_str = [str(e) for e in subtest]

                    start_time = time.time()
                    max_time = STUCK_LIMIT_MARK_TIME_SEC
                    self.logger.debug('Processing {} subtest{}'.format(count, '' if count == 1 else 's'))
                    while count > 0:
                        res = None
                        try:
                            got_index_subtest_id, res = q.get_nowait()
                            got_subtest_id = None

                            # code below operates on j variable, leaving it for consistency
                            j = got_index_subtest_id
                            # for safety reason check if what we have received is a tracking tuple (used when calling q.put())
                            if type(got_index_subtest_id) is tuple and len(got_index_subtest_id) == 2:
                                j, got_subtest_id = got_index_subtest_id
                            if got_subtest_id and (got_subtest_id in subtests_as_str):
                                subtests_as_str.remove(got_subtest_id)
                            count -= 1
                        except Empty:
                            # It was spotted that q.get() was blocking and left in that stuck condition forever
                            # hence get_nowait() and Empty exception handling.
                            if time.time() > start_time + max_time:
                                for proc in p:
                                    if proc.is_alive():
                                        self.logger.error(
                                            "Hanging process is {} with PID {} and name {}".format(
                                                str(proc), proc.pid, proc.name
                                            )
                                        )
                                # stuck can be caused by usage of PARALLEL tags, please review TC and remove them
                                msg = "Runner couldn't get {} subtest{} results from queue within {} seconds, which is limit for single subtest.".format(
                                    count, '' if count == 1 else 's', max_time
                                )
                                self.logger.error(msg)
                                self.logger.error("The following subtests did not finish on time as required:")
                                sub_msg = "\n"
                                for subtest_id in subtests_as_str:
                                    sub_msg += "{}\n".format(subtest_id)
                                self.logger.error(('-' * 80) + sub_msg[:-1])
                                self.logger.error('-' * 80)
                                raise Exception(msg)
                            time.sleep(1)
                            continue

                        if self.prompt != True:
                            self.number_of_subtests += 1
                            self.results.total_subtests += 1
                        if mode > 0:
                            self.print_verbose(res[0])
                        success = res[1]
                        if success is None and not res[2]:
                            # str or int test steps
                            continue
                        self.print_verbose(result=success)
                        if success is False or success is None or success is Exception:
                            # Test step failed or errored, handle that accordingly
                            if val == 2:
                                if i < (len(subtests) - 1):
                                    continue

                            # aggregate subtests status
                            if success is Exception:
                                new_retval = RETVAL_ERRORED
                            elif success is False:
                                new_retval = RETVAL_FAILURE
                            elif success is None:
                                # Special case for tests returning (None, ...).
                                # These tests are passing but log warning in logs.
                                new_retval = RETVAL_SUCCESS
                            else:
                                new_retval = RETVAL_SUCCESS
                            retval = max(new_retval, retval)

                            errors += res[2]
                            self.logger.info('*' * 80)
                            if success is None:
                                self.logger.warning('  WARNING')
                                self.logger.warning('*' * 80)
                                for entry in res[2]:
                                    self.logger.warning(entry)
                                self.logger.warning('*' * 80)
                            else:
                                self.failed_subtests += 1
                                self.results.failed_subtests += 1
                                self.logger.error('  FAILURE' if success is False else '  EXCEPTION')
                                self.logger.error('*' * 80)
                                for entry in res[2]:
                                    self.logger.error(entry)
                                self.logger.error('*' * 80)

                            # DEBUG CALLBACK
                            # Set Subtest Case Fail
                            subtest_fail = True

                            # Execute class-registered on-failure function if applicable
                            func = subtests[j][0]
                            try:
                                func_class = func.__self__
                            except AttributeError:
                                func_class = None
                            try:
                                failure_func = func_class.failures[func.__name__]
                                for func in failure_func:
                                    v = func()
                                    if v[0] is False:
                                        self.logger.error('%s failure: %s' % (func.__name__, v[1]))
                            except (KeyError, AttributeError):
                                pass

                            # report status based on CASE/CHECK/GROUP mode
                            # TODO: add E2E tests for this mode
                            if val == 3:
                                return 0
                            elif val == 1:
                                continue
                            else:
                                res = self.special_fail_cases(errors)
                                if res != 0:
                                    return res
                        else:
                            if val == 1 and val == 2:
                                return 0
                        self.print_verbose('\n')
                    # we should not see any alive processees as we are after while loop
                    # that collected all the results
                    for proc in p:
                        # call with arbitrary 5s timeout, to make sure we won't hang
                        proc.join(5)
                        if proc.is_alive():
                            self.logger.warning(
                                "Proc {} [pid:{}] is alive after termination".format(proc.name, proc.pid)
                            )
                            proc.terminate()
                            proc.join(5)
                            if proc.is_alive():
                                self.logger.warning(
                                    "Proc {} [pid:{}] is still alive after termination".format(proc.name, proc.pid)
                                )
            # DEBUG CALLBACK
            # If the subtest->Tests function has the callback attribute, run callback

            if subtest_fail:
                try:
                    if self.current_running_testcase.function.debug_callback:
                        debug_callback = self.current_running_testcase.function.debug_callback

                        module_name = debug_callback.__module__
                        function_name = debug_callback.__name__
                        callback_message = "Invoke Debug Callback '{}' From Module '{}' ".format(
                            function_name, module_name
                        )
                        self.logger.info(callback_message)
                        debug_callback()

                except Exception as e:
                    self.logger.error("Exec Callback Failed!")
                    self.logger.error(e)

                finally:
                    subtest_fail = False
            i += 1
        return retval

    def run_subtest(self, test, subtests, q, first_index, mode = 0):
        #mode 1 == PARALLEL
        #mode 2 == BLOCK
        i = first_index
        p = []
        # make sure clear everything
        SmartDebug.trace_lock(initial=True)
        if mode == 0:
            SmartDebug.set_sub_test(subtests)
            subtests = [subtests]
        elif mode == 2:
            machines_sessions = []
            sessions = self.ultimate['confd'].sessions
            for session_type in sessions:
                for machine in sessions[session_type]:
                    if sessions[session_type][machine]:
                        sessions[session_type][machine].terminated = True
        try:
            for subtest in subtests:
                if type(subtest) == str:
                    # putting tracking tuple on first place where i is index of subtest
                    # and subtest_id is string representation of a subtest,
                    q.put(((i, subtest), (subtest, None, [])))
                    i += 1
                    continue
                elif type(subtest) == int:
                    # putting tracking tuple on first place where i is index of subtest
                    # and subtest  is string representation of a subtest - here int value,
                    time.sleep(subtest)
                    q.put(((i, str(subtest)), ('%d sleep' % subtest, None, [])))
                    i += 1
                    continue
                func = subtest[0]
                args = subtest[1]
                result = subtest[2]
                try:
                    err_msg = subtest[3]
                except IndexError:
                    err_msg = None
                # string representation of subtest
                subtest_id = str(subtest)
                for machine in args:
                    if mode == 2:
                        if (machine in self.tb.machines()) and ( machine not in machines_sessions):
                            try:
                                sessions_set = self.get_all_sessions_for_a_machine(machine, True)
                            except Exception:
                                sessions_set = False
                            machines_sessions.append(machine)
                            if sessions_set is False:
                                # putting tracking tuple on first place where i is index of subtest
                                # and subtest_id is string representation of a subtest,
                                q.put(
                                    (
                                        (i, subtest_id),
                                        (
                                            '%s: %s %s' % (str(machine), func.__name__, str(args[machine])),
                                            False,
                                            ['Could not get a session'],
                                        ),
                                    )
                                )
                                continue
                    if mode != 1:
                        res = self.exec_subtest(machine, func, args[machine], result, err_msg, mode)
                        # putting tracking tuple on first place where i is index of subtest
                        # and subtest_id is string representation of a subtest,
                        # res is a result of subtest function call
                        q.put(((i, subtest_id), res))
                    else:
                        if len(p) >= MAX_NUM_OF_PROCS:
                            l = 0
                            while len(p) >= MAX_NUM_OF_PROCS:
                                if l == MAX_NUM_OF_PROCS:
                                    time.sleep(0.2)
                                    l = 0
                                if p[l].is_alive() is False:
                                    p.pop(l)
                                    break
                                l += 1
                        func_args = (machine, func, args[machine], result, err_msg, mode)
                        proc = multiprocessing.Process(
                            target=self.call_func_as_process,
                            name=subtest_id,
                            args=(self.exec_subtest, func_args, q, (i, subtest_id)),
                        )
                        proc.start()
                        p.append(proc)
                    i += 1
        except Exception:
            raise
        finally:
            if mode == 2:
                for mch in machines_sessions:
                    for session_type in ['confd', 'root', 'ncs', 'iosxe']:
                        self.close_session(mch, session_type)
        return p

    def exec_subtest(self, machine, func, args, result, err_msg, mode):
        # type: (str, typing.Callable, typing.Union[list, dict], bool, typing.Union[str, None], int) -> typing.Tuple[str, object, typing.List[str]]
        call_args_dict = self.get_call_args_dict(func, machine, args)
        call_args, call_kwargs = self.get_call_args_kwargs(func, call_args_dict)
        test_case_str = '%s: %s' % (machine, self.get_call_str(func, call_args_dict))

        sessions_set = False
        try:
            if mode == 1:
                if machine in self.tb.machines():
                    try:
                        sessions_set = self.get_all_sessions_for_a_machine(machine, True)
                    except Exception:
                        return (test_case_str, Exception, ['Could not get sessions to %s' % machine, traceback.format_exc()])
            elif mode == 0:
                self.print_verbose(test_case_str)
            self.print_func_name_to_logs(machine, func.__name__, args, True)
            if func.__name__.startswith('cnw_') and result is False:
                self.logger.warning(
                    'Executing cnw_* function (%s) with test expected value = False. '
                    'This might consume all timeout allocated for cnw_* function and in '
                    'consequence increase duration of a test suite which will be treated '
                    'as a performance problem. Check the logic!' % func.__name__
                )
            try:
                # Verify if confd session for the machine still alive
                confd_sessions = self.ultimate['confd'].sessions['confd']
                if confd_sessions.get(machine) and not confd_sessions[machine].isalive():
                    self.get_all_sessions_for_a_machine(machine, True)

                # Execute subtest
                with self.profiler.run_subtest(func.__name__):
                    retval = self.call(func, call_args, call_kwargs)

            except (pexpect.TIMEOUT, pexpect.EOF, OSError):
                if mode != 1:
                    self.logger.warning('Invalidating sessions after exception')
                    if machine in self.tb.machines():
                        try:
                            self.ultimate['confd'].sessions['confd'][machine].close()
                            if self.ultimate['confd'].sessions['confd'][machine].isalive() is False:
                                confd_log = self.ultimate['confd'].sessions['confd'][machine].logfile
                                self.ultimate['confd'].sessions['confd'][machine] = self.tb.get_machine_session(
                                    machine, MACHINE_SESSION_PEXPECT_TIMEOUT, confd_log, False, True, False
                                )
                        except KeyError:
                            if type(machine) == str and (machine in ['All', 'SPIRENT', 'TestBedHost', 'Protractor', 'HTTP', 'LANDSLIDE', 'VMANAGE_HTTP_SERVER', 'JMETER', 'VMANAGE_HTTP_CLUSTER', 'NA', 'IXIA']):
                                pass
                            else:
                                self.ultimate['confd'].sessions['confd'][machine] = self.tb.get_machine_session(
                                    machine, MACHINE_SESSION_PEXPECT_TIMEOUT, None, False, True, False
                                )
                raise

            # Sanity check retval
            if not isinstance(retval, (list, tuple)) or len(retval) < 2:
                raise ValueError("Wrong return type in the test script. Expected (bool, str), was {!r}".format(retval))

            path = self.tc_src_code_logger.get_function_src_file(func)

            if not err_msg:
                err_msg = retval[1]

            errors = [
                'Machine         : %s' % machine,
                'Action          : %s%s' % (func.__name__, args),
                'Full action     : %s' % test_case_str,
                'Path            : %s' % Paths().vtest_relative(path),
                'Expected result : %s' % result,
                'Result          : %s' % retval[0],
                'Error           : %s' % err_msg,
            ]

        except RuntimeError:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            exc_traceback_stack_str = traceback.format_exc()
            SmartDebug.set_exception(exc_type, exc_obj, exc_traceback_stack_str)
            SmartDebug.analyze(exc_traceback_stack_str)
            return (test_case_str, Exception, [exc_traceback_stack_str])
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            exc_traceback_stack_str = traceback.format_exc()
            SmartDebug.set_exception(exc_type, exc_obj, exc_traceback_stack_str)
            SmartDebug.analyze(exc_traceback_stack_str)
            return (test_case_str, Exception, [exc_traceback_stack_str])
        finally:
            if mode == 1:
                if sessions_set:
                    for session_type in ['confd', 'ncs', 'root', 'iosxe']:
                        self.close_session(machine, session_type)

        if retval[0] is None or retval[0] != result:
            # set tc fail

            # Fail, collect function trace
            SmartDebug.analyze(retval)
            misc.cur_testcase.set_tc_state(state=False, case="", step=test_case_str, forced=False)

        if retval[0] is None:
            return (test_case_str, None, errors)

        return (test_case_str, retval[0] == result, errors)

    @staticmethod
    def get_call_args_dict(func, machine, args):
        # type: (typing.Callable, str, typing.Union[dict, list]) -> dict
        # Dont enforce mandatory "machine" param for some cases
        if machine in ['NA', 'IXIA']:
            if isinstance(args, dict):
                # If functions arguments are passed as dict
                retval = inspect.getcallargs(func, **args)
            else:
                # If functions arguments are passed as list
                retval = inspect.getcallargs(func, *args)
        else:
            if isinstance(args, dict):
                # If functions arguments are passed as dict
                retval = inspect.getcallargs(func, machine, **args)
            else:
                # If functions arguments are passed as list
                retval = inspect.getcallargs(func, machine, *args)
        return retval

    @staticmethod
    def get_call_args_kwargs(func, call_args_dict):
        # type: (typing.Callable, dict) -> typing.Tuple[list, dict]
        to_consume = call_args_dict.copy()
        if sys.version_info[0] < 3:
            argspec = inspect.getargspec(func)
            keywords = argspec.keywords
        else:
            argspec = inspect.getfullargspec(func)
            keywords = argspec.varkw
        args = []
        kwargs = {}
        for a in argspec.args:
            args.append(to_consume.pop(a))
        if argspec.varargs:
            args += to_consume.pop(argspec.varargs)
        if keywords:
            kwargs = to_consume.pop(keywords)
        return args, kwargs

    @staticmethod
    def get_call_str(func, call_args):
        # type: (typing.Callable, dict) -> str
        argspec = inspect.getargspec(func)
        arg_names = argspec.args[:]
        # varargs and keywords generally does not appear in vTest codebase, but support is kept
        if argspec.varargs:
            arg_names += [argspec.varargs]
        if argspec.keywords:
            arg_names += [argspec.keywords]
        args_str = ", ".join("{n}={v!r}".format(n=n, v=call_args[n]) for n in arg_names)

        # remove wrapper if there is a one
        if func.__name__ == '_wrapper_func':
            func_name = func.__self__.a_func.__name__
        else:
            func_name = func.__name__

        return "{fname}({fargs})".format(fname=func_name, fargs=args_str)

    @staticmethod
    def call(func, call_args, call_kwargs):
        # type: (typing.Callable, list, dict) -> typing.Any
        f = func.__func__ if inspect.ismethod(func) else func  # type: ignore
        with SmartDebug.trace():
            return f(*call_args, **call_kwargs)

    def special_fail_cases(self, errors):
        if self.first_fail:
            return -1
        elif self.interactive:
            self.logger.warning('The test failed')
            self.logger.info('The script has been paused for you to perform manual checks')
            options = 'Choose one of the following options:\n'
            options += '[x] to stop the script and exit\n'
            options += '[c] to continue executing the script\n'
            options += '[s] to skip to the next test\n'
            options += '[p] to print the current failure\n'
            options += '[i] to open an interactive prompt session\n'
            options += '>>> '
            while True:
                entry = input(options)
                if entry == 'x':
                    return -1
                elif entry == 'c':
                    return 0
                elif entry == 's':
                    return 2
                elif entry == 'p':
                    print('')
                    for entry in errors[-4:]:
                        print(entry)
                elif entry == 'i':
                    try:
                        code.interact(local = dict(globals(), **locals()))
                    except SystemExit:
                        return 0
        return 0

    def copy_console_logger_logs(self):
        """Kills all console logger sessions for the testbed"""
        failure_strings = ['Kernel panic', 'Fatal', 'Unable']
        self.logger.info('Copying console log files to the log directory for the current run')
        for machine in self.tb.machines():
            if 'pm' in machine:
                source_file = os.path.join(self.tb.workdir, machine, 'console_output')
                destination_file = os.path.join(self.logs_sub_dir, 'console_output_%s' % machine)
                if os.path.isfile(source_file):
                    console_log_file = open(source_file, 'r')
                    console_log_contents = console_log_file.read()
                    if console_log_contents:
                        self.logger.warning("Console log %s isn't empty: %s"%(destination_file, console_log_contents))
                    console_log_file.close()
                    for failure_string in failure_strings:
                        if failure_string in console_log_contents:
                            self.logger.warning('Check console log for %s, a failure string was detected!' % machine)
                            self.logger.warning(destination_file)
                    shutil.copy(source_file, destination_file)
                else:
                    self.logger.info('The console log for %s was not created' % machine)

    def log_errors(self, errors, print_err = True):
        """Stores all errors from testing"""
        for item in errors:
            self.errors_list.append(item)
            if print_err:
                self.logger.error(item)

    def log_warnings(self, warnings):
        """Stores all warnings from testing"""
        for item in warnings:
            self.warnings_list.append(item)
            self.logger.warning(item)

    def print_test_name_verbose(self, name):
        """Prints the current test name to the verbose output"""
        self.print_verbose()
        self.print_verbose('-'*50)
        self.print_verbose("{} ({}/{})".format(name, self.number_of_test_cases, self.tests_in_suite))
        self.print_verbose('-'*50)

    def get_testbed(self):
        """Gets the name of the testbed that is up"""
        if not self.lock.locked():
            self.logger.error('No running testbed found')
            return None

        testbed = str(self.lock.testbed)
        if os.path.exists(testbed):
            return testbed
        self.logger.error('testbed "{}" owns the lock, but does not exist'.format(testbed))
        self.lock.release()
        return None

    def print_verbose(self, *args, **kargs):
        """Prints test and subtest info when the verbose option is selected"""
        string = ''
        if 'result' in kargs:
            stream_handlers = []
            other_handlers = []
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream.isatty():
                    stream_handlers.append(handler)
                else:
                    other_handlers.append(handler)
            for handlers in [stream_handlers, other_handlers]:
                for handler in handlers:
                    self.logger.removeHandler(handler)
                if kargs['result']:
                    if handlers != stream_handlers:
                        string = Color.GREEN + '[PASS]' + Color.RESET
                    else:
                        string = '[PASS]'
                    self.logger.info(string)
                elif kargs['result'] is None:
                    if handlers != stream_handlers:
                        string = Color.YELLOW + '[WARNING]' + Color.RESET
                    else:
                        string = '[WARNING]'
                    self.logger.warning(string)
                elif kargs['result'] is False:
                    if handlers != stream_handlers:
                        string = Color.RED + '[FAIL]' + Color.RESET
                    else:
                        string = '[FAIL]'
                    self.logger.error(string)
                elif kargs['result'] is Exception:
                    if handlers != stream_handlers:
                        string = Color.BG_RED + '[ERROR]' + Color.BG_RESET
                    else:
                        string = '[ERROR]'
                    self.logger.error(string)
                else:
                    if handlers != stream_handlers:
                        string = Color.YELLOW + '[UNKNOWN]' + Color.RESET
                    else:
                        string = '[UNKNOWN]'
                    self.logger.warning(string)

                for handler in handlers:
                    self.logger.addHandler(handler)
        else:
            for arg in args:
                string += ' ' + str(arg)
                string = string.strip()
            if len(string) > 3000:
                self.logger.warning("The argument was too large to print to the terminal")
            else:
                self.logger.info(string)

    def print_line(self, arg = None, char = '*'):
        """Prints a line of the specified chars"""
        string = '''\n'''
        string +=  char * 78 + '\n'
        if arg is not None:
            string += arg + '\n'
            string += char * 78
        return string.strip()

    def _prepare_test_result_summary(self):
        # type: () -> str
        """Prepares table with test result summary."""
        summary = [
            "",
            "---------------------",
            "Test results summary:",
            "---------------------",
            "Total Tests              : {}".format(self.results.total_tests),
            "Executed                 : {}".format(self.results.executed),
            "Skipped                  : {}".format(self.results.skipped),
            "Passed                   : {}".format(self.results.passed),
            "Failed                   : {}".format(self.results.failed),
            "Aborted                  : {}".format(self.results.aborted),
            "Errored                  : {}".format(self.results.errored),
            "Blocked                  : {}".format(self.results.blocked),
            "Executed percentage      : {}".format(self.results.executed_percentage),
            "Executed percentage pass : {}".format(self.results.executed_percentage_pass),
            "Overall percentage pass  : {}".format(self.results.overall_percentage_pass),
        ]
        summary = '\n'.join(summary)
        self.logger.info(summary)
        return summary

    def _prepare_subtests_summary(self):
        # type: () -> None
        """Prepares and logs summary of executed subtests."""
        summary = [
            "",
            "---------------------",
            "  Subtests summary:  ",
            "---------------------",
            "Total subtests               : {}".format(self.results.total_subtests),
            "Subtests executed in parallel: {}".format(self.results.parallel_subtests),
            "Parallel subtests percentage : {}".format(self.results.parallel_subtests_percentage),
        ]
        summary = "\n".join(summary)
        self.logger.info(summary)

    def _prepare_version_skipped_summary(self):
        # type: () -> None
        """Prepares and logs summary of test skipped due to version check."""
        summary = [
            "",
            "--------------------------------------",
            "  Test skipped due to version check:  ",
            "--------------------------------------",
            "Total test skipped due to version check: {}".format(len(self.results.version_skipped)),
            "Skipped tests:",
        ]
        for skipped in self.results.version_skipped:
            summary.append("- {}".format(skipped))
        summary = "\n".join(summary)
        self.logger.info(summary)

    def _log_run_links(self):
        # type: () -> None
        """Logs table with external links related to current run."""
        if self.db_write:
            self.logger.info("Run log: {}".format(self.run_log))
            self.logger.info("RegressDB: {}".format(self.db_url))
            self.logger.info("New RegressDB: {}".format(self.regressdb_api_url))
            # TODO: awaiting integration with p3 branch of vTest
            # AtomicHistory(VLogging.path).update_entry({'link': self.db_url})

    def print_test_stats(self):
        # type: () -> str
        """Reports test results and links to current run.

        Reports are added to XML report and printed as table to console.
        """
        self.summary.save_results_to_xml(self.results, self.core_found)
        summary = self._prepare_test_result_summary()
        self._prepare_subtests_summary()
        if self.results.version_skipped:
            self._prepare_version_skipped_summary()
        self._log_run_links()

        return summary

    def error(self, errmsg):
        """Returns a formatted error message string"""
        return 'Error: ' + str(errmsg)

    def back_to_base(self):
        """ """
        try:
            self.tb
        except AttributeError:
            testbed = self.get_testbed()
            if testbed is None:
                self.logger.error('No testbed is up')
                return 1
            self.tb = HyperVisor(testbed, self.debug, log_root=self.logs_sub_dir)
            res = self.tb.get_all_mchs_sessions()
            if res == -99:
                return res
            confd_machine_sessions = res
            confd = CONFDSession(self.tb, {'confd': confd_machine_sessions}, False, None)
            self.ultimate = {}
            self.ultimate['confd'] = confd
            self.ultimate['sessions'] = {'confd': confd_machine_sessions}
            self.ultimate['root_sessions'] = []
        res = self.load_all_configs(config_name = 'blank_config')
        if len(self.ultimate) == 2:
            for machine in self.tb.machines():
                self.close_session(machine)
            del self.ultimate
        return res

    def get_user_and_branch(self):
        # type: () -> Tuple[Optional[str], str]
        """
        Returns current vtest workspace branch name and OS user name
        """
        user_name = os.environ.get("USER")
        # Used git command instead of git python module to avoid the necessity
        # to install additional modules in already existing virtual envs
        current_branch = (
            subprocess.Popen(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stdout=subprocess.PIPE,
                cwd=os.path.abspath(os.path.dirname(__file__)),
            )
            .communicate()[0]
            .decode("utf-8", errors='ignore')
            .strip()
        )

        return (user_name, current_branch)

    def _update_build_version(self, db_handle):
        """
        Update regressdb build version based on branch value.

        This is used to have build version updated to regressdb at the beginning of run (before vms are spawned).
        It is required for run results analysis which is based on build version.
        Later on, when vms are spawned, it will be updated in regressdb by proper version fetched from devices.

        Image location is fetched from preference.yaml file then get_location_version is used
        to get build version for this location and regressdb is updated with this value.
        """
        self.logger.info("Getting build version based on branch: %s" % self.args.branch)
        image_location = pref.get("images", {}).get(self.args.branch, {}).get("loc")
        branch_version = get_location_version(image_location)
        if branch_version:
            self.logger.info("Updating build version in DB: Build version based on branch: %s" % branch_version)
            db_handle.update_build_to_db(self.db_build_id, branch_version, self.db_tb_name)

    def store_results(self, mode, trace=False, tags = None, message = None):
        """
        Store the results for this run in the regressdb, if this is running on a server.
        Also send out a results email if the -U option was specified
        """
        if not self.db_write:
            self.logger.warning('Flag no_regressdb is set')
            self.logger.warning("Due to above:")
            self.logger.warning("\tregress DB ID (db_build_id) will not be available")
            self.logger.warning("\tvTest monitor won't start")
            self.logger.warning("\tthere will be no logs backup to NFS")
            return 0

        db_run_log = ''
        logs_dir = os.path.basename(self.logs_sub_dir)
        ip = self.get_testbed_ip_addr(self.tb_hostname)
        if ip is None:
            log = os.path.join(self.logs_sub_dir, 'run.log')
            fqdn = socket.getfqdn()
            run_log = '%s/logs/%s/run.log' % (fqdn, logs_dir)
        else:
            run_log = '%s/logs/%s/run.log' % (ip, logs_dir)
            log = '<a href="http://%s">%s</a>' % (run_log, run_log)
        db_run_log = 'http://%s' % run_log
        self.run_log = db_run_log

        if self.db_write and not self.db_wrote:
            # FIXME - Temporary change to avoid changes in
            # mysql database schema and vip-oldregressdb. The data will be
            # presented on Job Description in vip-oldregressdb as a comment.
            db_user_name, db_current_branch = self.get_user_and_branch()
            if self.message is None:
                self.message = ""

            self.db_suite = self.suite
            self.db_build_id = None
            full_run_cmd = self.executor + " " + self.args_string
            bugbuddy_status = self.bugbuddy_util.get_status()
            try:
                with self.get_db_client() as db_handle:
                    db_handle.push_build_to_db(
                        self.db_build,
                        self.tb_hostname,
                        self.db_suite,
                        self.db_search_date,
                        full_run_cmd,
                        db_run_log,
                        db_user_name,
                        db_current_branch,
                        bugbuddy_status,
                    )
                    self.db_build_id = db_handle.fetch_build_id(
                        self.db_build, self.tb_hostname, self.db_suite, self.db_search_date
                    )
                    GlobalParam().db_build_id = self.db_build_id
                    if self.db_build_id:
                        self.logger.info(
                            "ID {} retrieved from regressDB, launching vTest monitor".format(self.db_build_id)
                        )
                        self.vmonitor = launch_vmonitor(self.logger, self.db_build_id, Paths().current_logs())
                    if not self.db_build and self.args.branch:
                        self._update_build_version(db_handle)
                    db_handle.update_blogs_to_db(self.db_build_id, "", "Log backup pending, tests running...")
                    db_handle.update_comment_to_db(self.db_build_id, self.message)
                    self.db_wrote = True
            except Exception:
                self.logger.warning("Failed to update DB", exc_info=True)

            db_url = 'vip-oldregressdb.cisco.com:8080/regressdb/%s/' % self.db_build_id
            self.db_url = "http://%s" % db_url
            self.regressdb_api_url = "http://regressdb-api.cisco.com:3000/jobs/%s" % self.db_build_id
            self.db_log = '<a href="http://%s">%s</a>' % (db_url, db_url)
            self.logger.info("log url: %s" % db_run_log)
            self.logger.info("DB Url: http://%s" % (db_url))
            self.logger.info("New RegressDB URL: %s" % (self.regressdb_api_url))
            self.send_status_to_github_endpoint("pending")
            self.send_comment_to_github_endpoint('scheduled')
            self.call_runner_helper("start")
        if bool(self.recipient):
            #Send an email for this run if a recipient was specified
            self.send_email(mode, log, trace, tags, message)

        if 'test_suites' in pref and self.suite in pref['test_suites'] and 'subscribe_email' in pref['test_suites'][self.suite]:
            # Send mails to subscribed email-ids for this suite in pref yaml
            rcp = pref['test_suites'][self.suite]['subscribe_email']

            self.send_email(mode, log, trace, tags, message, rcp)
        
        notify_user_by_webex(
            mode,
            message,
            self.webex_id,
            self.start,
            self.db_build_id,
            self.tb_hostname,
            self.test_stats,
            self.db_test_suite_result,
        )

    def send_comment_to_github_endpoint(self, comment):
        notify_user_by_webex(
            comment,
            self.message,
            self.webex_id,
            self.start,
            self.db_build_id,
            self.tb_hostname,
            self.test_stats,
            self.db_test_suite_result,
        )
        if self.github_comment_endpoint is None:
            return
        githubToken = 'fbbeeea9948fb5c4a0f6df3291fbf7e86d175677'
        if self.suite == 'vexpress':
            suiteName = 'vExpress'
        else:
            suiteName = self.suite
        commentData = {"body": "%s: %s\n %s" %(suiteName, comment, self.db_url)}
        commentJSON = json.dumps(commentData)
        cmd = 'curl -sS -H "Authorization: token {token}" -X POST -H "Content-Type: application/json" --data \'{data}\' {endpoint}'
        cmd = cmd.format(token=githubToken, data=commentJSON, endpoint=self.github_comment_endpoint)
        out = subprocess.call(cmd, shell= True)
        if out != 0:
            return [False, 'Failed to send comment to GitHub']
        else:
            return [True, 'Successfully sent comment to GitHub']

    def send_status_to_github_endpoint(self, statusType):
        if self.github_status_endpoint is None:
            return
        githubToken = 'fbbeeea9948fb5c4a0f6df3291fbf7e86d175677'
        if self.suite == 'vexpress':
            githubContext = '{}-{}'.format('vExpress', self.branch)
        else:
            githubContext = '{}-{}'.format(self.suite, self.branch)
        statusData = {"state":"%s" % statusType,
                      "target_url":"%s" % self.db_url,
                      "description":"%s job %s: %s" % (githubContext,
                                                       self.db_build_id,
                                                       statusType),
                      "context":githubContext}
        self.logger.info("Sending status to GitHub")
        self.logger.info("Status: {}".format(statusType))
        self.logger.info(statusData)
        statusJSON = json.dumps(statusData)
        cmd = 'curl -sS -H "Authorization: token {token}" -X POST -H "Content-Type: application/json" --data \'{data}\' {endpoint}'
        cmd = cmd.format(token=githubToken, data=statusJSON, endpoint=self.github_status_endpoint)
        out = subprocess.call(cmd, shell= True)
        if out != 0:
            return [False, 'Failed to send status to GitHub']
        else:
            return [True, 'Successfully sent status to GitHub']

    def send_email(self, mode, log, trace=False, tags=None, message=None, recipient=None):
        """Sends email notifications when remote tests are run"""
        if recipient is None:
            recipient = self.recipient
        subject = self.tb_hostname
        if mode == 'start':
            subject += ' - Started tests '
            stats = ''
        elif mode == 'stop':
            mchL = self.tb.machines()
            if hasattr(self, 'ultimate'):
                if self.suite == 'cExpress':
                    cedge_list = list(filter(self.tb.is_cedge, list(self.tb.machines().keys())))
                    swver = self.ultimate['confd'].show_version(cedge_list[0], 'False')[1]
                else:
                    swver = self.ultimate['confd'].show_version(list(mchL.keys())[0], 'False')[1]
            else:
                swver = 'unknown sw ver'
            stats = self.print_test_stats()
            if self.results.failed_subtests == 0 and self.results.executed != 0 and trace is False:
                subject += ' - Tests Successful %s' % swver
            else:
                subject += ' - Tests Failed %s' % swver
                if len(self.warnings_list) > 0:
                    subject += ' - Script Warning'
                if trace:
                    subject += ' - Script Error'
                    stats = traceback.format_exc()
                    stats = re.sub('\\n', '<br>', stats)
                error_str = '<br>'.join(map(str, self.errors_list))
                stats += '<br>' + error_str
        else:
            stats = mode

        content = 'Suite: %s <br> Testbed: %s <br>' % (self.suite, os.path.basename(self.tb.workdir))
        content += 'Tags: %s <br> Message: %s <br> %s <br>' % (tags, message, stats)
        content += 'To access the log for this run go to %s %s' % (self.tb_hostname, log)
        content += '<br>To access the db log for this run go to %s </br>' % (self.db_log)

        sender = pref['sender']
        headers = email.mime.text.MIMEText(content, 'html')
        headers['From'] = sender
        headers['Subject'] = subject
        headers['To'] = ', '.join(recipient)
        email_sending_attempt = 1
        email_sent = False
        while not email_sent and email_sending_attempt <= 2:
            session = None
            try:
                self.logger.info("Trying to send email, attempt: {}".format(email_sending_attempt))
                subprocess.call('nslookup mail.cisco.com', shell = True)
                session = smtplib.SMTP('mail.cisco.com', 25, timeout=10)
                session.set_debuglevel(False)
                session.sendmail(sender, recipient, headers.as_string())
                email_sent = True
            except Exception:
                import traceback
                self.logger.warning('Could not send a %s email' % mode)
                print(traceback.format_exc())
            finally:
                if session:
                    session.quit()
                email_sending_attempt += 1

    def backup_core_files(self, remove_cores = False):
        """Backs up all core files to old_dumps on each machine"""
        q = multiprocessing.Queue(len(self.tb.machines()))
        p = []
        for machine in self.tb.machines():
            if self.tb.is_ucs(machine):
                continue
            if self.tb.is_cedge(machine):
                dst = os.path.join(self.logs_sub_dir, 'core_files', machine, 'before_tests')
                proc = Thread(
                    target=self.call_func_as_process, args=(self.check_and_get_core_files, (machine, dst), q, machine)
                )
            else:
                proc = multiprocessing.Process(target = self.call_func_as_process, args = (self.tb.backup_core_files, (machine, remove_cores), q, machine))
            proc.start()
            p.append(proc)
        for proc in p:
            proc.join()
        while q.empty() is False:
            result = q.get()
            id = result[0]
            res = result[1]
            if res[0] is False:
                self.logger.warning("{} core files: {}".format(id, res[1]))

    def call_func_as_process(self, func, args, q, identifier = None):
        res = func(*args)
        if identifier is None:
            q.put(res)
        else:
            q.put((identifier, res))

    def check_processes(self, script):
        """Checks to make sure there are no core files and all daemons are still running"""
        errors = []
        heading = self.print_line('Process Errors')
        self.logger.info('Making sure all daemons are still running and checking for core files...')
        if self.ultimate['api'] is not None:
            self.check_running_daemons(errors)
        self.check_core_files(errors)
        #Commenting this out till vconfd error is resolved
        #self.check_errors_in_logs_files('')
        self.number_of_tests += 1
        if len(errors) > 0:
            errors.insert(0, heading)
            self.errors_list.append(script.upper())
            self.results.failed_subtests += 1
            self.log_errors(errors)
            self.number_of_failed_tests += 1
            return 1
        return 0

    def check_core_files(self, errors, dst=None):
        """Checks to make sure there are no core files, for each machine, and if core files exist they are transfered to the host"""
        final_result = False
        q = multiprocessing.Queue(len(self.tb.machines()))
        p = []
        for machine in self.tb.machines():
            if dst is None:
                proc = multiprocessing.Process(
                    target=self.call_func_as_process, args=(self.check_and_get_core_files, (machine,), q)
                )
            else:
                machine_core_dst = os.path.join(dst, machine)
                if self.tb.is_cedge(machine):
                    proc = Thread(
                        target=self.call_func_as_process,
                        args=(self.check_and_get_core_files, (machine, machine_core_dst), q),
                    )
                else:
                    proc = multiprocessing.Process(
                        target=self.call_func_as_process,
                        args=(self.check_and_get_core_files, (machine, machine_core_dst), q),
                    )
            proc.start()
            p.append(proc)
        for proc in p:
            proc.join()
        while q.empty() is False:
            result = q.get()
            if result[0] is False:
                # Set core found flag as well
                self.core_found = True
                self.db_core_found = "Core Found"
                errors.append(result[1])
                final_result = True
        core_files_dir = os.path.join(self.logs_sub_dir, 'core_files')
        try:
            if self.server and os.path.isdir(core_files_dir):
                self.tb.sudo(['sudo','chmod','-R','777','%s' % core_files_dir], shell = True)
        except KeyError:
            pass
        if final_result:
            return 1
        return 0

    def check_and_get_core_files(self, machine, dst=None):
        if dst is None:
            dst = os.path.join(self.logs_sub_dir, 'core_files', machine)
        if self.tb.is_ucs(machine):
            return [True, 'TBD']
        if not self.tb.mgmt_ipaddr(machine):
            return [True, "Skipped downloading core files. Machine {} doesn't have mgmt ip in topology yaml"]
        if self.tb.is_cedge(machine):
            return self.check_and_get_core_files_from_cedge(machine, dst)
        else:
            return self.check_and_get_core_files_from_vedge(machine, dst)

    def check_and_get_core_files_from_vedge(self, machine, dst=None):
        result = self.tb.check_core_files_on_vedge(machine)
        if result[0] is False:
            self.get_core_files_from_vedge(machine, dst)
        return result

    def check_and_get_core_files_from_cedge(self, machine, dst):
        """
        Check and get core files from cEdge.

        Args:
            machine (str): The name of the machine.
            dst (str): The destination directory to copy the admin-tech files.

        Returns:
            list: A list containing two elements:
                - A boolean indicating whether core files were found or not.
                - A list of core file names.

        Raises:
            Exception: If an error occurs while checking core files.

        """
        core_files = []
        log_dir = os.path.join(self.logs_sub_dir, machine)
        self.tb.mkpath(log_dir)
        log_file_path = os.path.join(log_dir, 'collect_cores.log')

        with open(log_file_path, 'a+') as log_file:
            try:
                session = self.tb.get_iosxe_cli_session(machine, 300, log_file)
                sessions = {'iosxe': {machine: session}}
                iosxe_session = IOSXESession(self.tb, sessions, self.logger)

                core_files = iosxe_session.list_core_files(machine)

                # Due to https://cdetsng.cisco.com/summary/#/defect/CSCwn32324 ,
                # if harddisk is present in the system, core will be looked up on it, but we
                # still want to log warnings if any cores are found on bootflash, this is for user awareness.
                if iosxe_session._core_src == 'harddisk' and iosxe_session._core_files_bootflash:
                    self.logger.warning(
                        "runner: Additional core files found on bootflash of {}: {}".format(
                            machine, iosxe_session._core_files_bootflash
                        )
                    )
                if len(core_files) > 0:
                    try:
                        self.logger.warning("runner: Core files found on {}: {}".format(machine, core_files))
                        self.tb.mkpath(dst)
                        self.get_cedge_admin_tech(machine, dst)
                        self.logger.info("runner: Admin-tech[s] are copied to {}".format(dst))
                    finally:
                        session.close()
                        self.logger.info("runner: Closed session for {}.".format(machine))
                        return [False, core_files]
                else:
                    self.logger.info("runner: No core files in %s" % machine)
                    session.close()
                    self.logger.info("runner: Closed session for {}.".format(machine))
                    return [True, core_files]
            except Exception as e:
                self.logger.exception("runner: Error while checking core files on {}: {}. ".format(machine, e))
                return [False, "runner: Error while checking core files on {}".format(machine)]

    def get_core_files_from_vedge(self, machine, dst=None):
        """
        Retrieves core files from a specified machine and copies
        them to a destination directory.

        Args:
            machine (str): Machine to retrieve core files from.
            dst (str, optional): The destination directory to copy the core files to.
            If not provided, the core files will be copied to a subdirectory
            named 'core_files' in the logs directory.

        Raises:
            Exception: If an error occurs while retrieving or copying the core files.

        """
        try:
            self.logger.info('runner: Starting to get core files from {}. '.format(machine))
            src = '/var/crash/*core* /var/crash/*info*'
            if dst is None:
                dst = os.path.join(self.logs_sub_dir, 'core_files', machine)
            self.logger.info('runner: Destination directory for core files: {}.'.format(dst))
            self.tb.mkpath(dst)
            self.tb.scp_from_machine(machine, src, dst, quiet=True, expect_timeout=300)
            self.logger.info('runner: Successfully copied core files from {} to {}. '.format(machine, dst))
            self.tb.call(machine, 'rm -f %s' % src)
            self.logger.info('runner: Removed core files from {}: {}. '.format(machine, src))
        except Exception as e:
            self.logger.exception('runner: Error while getting core files from {} with error: {}. '.format(machine, e))

    def check_running_daemons(self, errors):
        """Checks to make sure all daemons are running per machine personality"""
        final_result = True
        api = self.ultimate['api']
        vdaemons = api.vdaemon()
        vedge = ['ompd', 'ttmd', 'cfgmgr', 'zebra', 'ospfd', 'bgpd', 'ftmd', 'vrrp', 'sysmgrd', 'confd']
        vsmart = ['ompd', 'ttmd', 'cfgmgr', 'sysmgrd', 'confd']
        vbranch = ['cfgmgr', 'zebra', 'ospfd', 'bgpd', 'sysmgrd', 'confd']
        q = multiprocessing.Queue(len(self.tb.machines()))
        p = []
        for machine in api.machines():
            if vdaemons is not None:
                try:
                    vtype = api.vdaemon_vtype_from_machine(machine)
                    if vtype == 'vsmart' or vtype == 'vbond':
                        daemons = vsmart + ['vdaemon']
                    elif vtype == 'vmanage':
                        daemons = vsmart + ['vdaemon']
                        daemons.remove('ompd')
                        #CHANGE: Ask about this and then maybe remove it
                        daemons.remove('ttmd')
                    else:
                        if machine.startswith("vm"):
                            daemons = vedge + ['vdaemon', 'fp-um']
                        else:
                            daemons = vedge + ['vdaemon']
                except KeyError:
                    daemons = vbranch
            else:
                daemons = vbranch
            proc = multiprocessing.Process(target = self.call_func_as_process, args = (self.tb.check_processes_running, (machine, daemons), q, machine))
            proc.start()
            p.append(proc)
        for proc in p:
            proc.join()
        while q.empty() is False:
            machine, result = q.get()
            if result[0] is False:
                self.db_core_found += "\nProcess dead"
                errors.append(machine + ' : ' + result[1])
            final_result = final_result and result[0]
        if final_result is False:
            return 1
        return 0

    def get_var_logs(self):
        """Transfers var logs from each machine to the host"""
        p = []
        q = queue.Queue(len(self.tb.machines()))
        for machine in self.tb.machines():
            dst = os.path.join(self.logs_sub_dir, machine, f'var_logs_admin_tech_{machine}', 'admin-tech.tar.gz')
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)
            if self.tb.is_ucs(machine) or self.tb.is_highrise(machine):
                continue
            if self.tb.is_cedge(machine):
                all_args = (self.collect_data_from_cedge, (machine, dst), q, machine)
            else:
                all_args = (self.get_admin_tech, (machine, dst), q, machine)
            proc = Thread(target=self.call_func_as_process, args=all_args)
            proc.start()
            p.append(proc)
        for proc in p:
            proc.join()
        while q.empty() is False:
            machine, result = q.get()
            if type(result) == int and result > 1:
                self.logger.error('Could not get admin-tech for %s' % machine)

    def collect_crft(self):
        cedges = [m for m in self.tb.machines() if self.tb.is_cedge(m)]
        p = []
        q = queue.Queue(len(cedges))
        local_crft_dir = os.path.join(self.logs_sub_dir, "crft")
        self.tb.mkpath(local_crft_dir)
        crft_files = {}
        for machine_name in cedges:
            all_args = (self.collect_crft_from_cedge, (machine_name, local_crft_dir), q, machine_name)
            proc = Thread(target=self.call_func_as_process, args=all_args)
            proc.start()
            p.append(proc)
        for proc in p:
            proc.join()
        while q.empty() is False:
            machine_name, result = q.get()
            crft_files[machine_name] = [
                result,
            ]
        raw_versions = self.get_cedge_raw_versions()
        with open(os.path.join(local_crft_dir, 'raw_versions.json'), 'w') as f:
            f.write(json.dumps(raw_versions))
        if self.crft_taas_export:
            self.crft_taas_upload(crft_files, local_crft_dir, raw_versions)


    def create_taas_results_json(self):
        current_time = time.time()
        data = {
            'version': '3.2',
            'report': {
                'id': '{}.{}'.format(self.db_test_suite, self.db_build_id),
                'name': self.db_test_suite,
                'starttime': datetime.datetime.fromtimestamp(self.start).strftime('%Y-%m-%d %H:%M:%S.%f%z'),
                'stoptime': datetime.datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S.%f%z'),
                'host': self.tb_hostname,
                'extra': {
                    'testbed': self.tb_hostname,
                },
                'runtime': current_time - self.start,
                'submitter': 'tester',
                'summary': {
                    'passed': self.results.passed,
                    'passx': 0,
                    'failed': self.results.failed,
                    'errored': self.results.errored,
                    'aborted': self.results.aborted,
                    'blocked': self.results.blocked,
                    'skipped': self.results.skipped,
                    'total': self.results.total_tests,
                    'success_rate': self.results.executed_percentage_pass,
                },
            },
        }
        return json.dumps(data)

    def notify_taas(self, local_crft_yaml):
        upload_url = 'https://ngdevx.cisco.com/services/taas/api/v1/upload/results'
        api_timeout = 30
        tmp_dir_path = '/tmp/' + ''.join(random.choice(string.letters) for _ in range(10))
        try:
            os.mkdir(tmp_dir_path)
            shutil.copy(local_crft_yaml, tmp_dir_path)
            taas_json_data = self.create_taas_results_json()
            with open(os.path.join(tmp_dir_path, 'results.json'), 'w') as f:
                f.write(taas_json_data)
            archive_file = os.path.join(tmp_dir_path, 'archive.zip')
            zipf = zipfile.ZipFile(archive_file, mode='w', compression=zipfile.ZIP_DEFLATED)
            zipf.write(os.path.join(tmp_dir_path, 'results.json'), arcname='results.json')
            zipf.write(os.path.join(tmp_dir_path, 'crft.yaml'), arcname='crft.yaml')
            zipf.write(os.path.join(self.logs_sub_dir, "run.log"), arcname='run.log')
            zipf.close()
            data = {
                'url': upload_url,
                'timeout': api_timeout,
                'files': {
                    'file': (os.path.basename(archive_file), open(archive_file, 'rb'), 'application/zip'),
                    'format': (None, 'raw'),
                    'timestamp': (None, int(time.time())),
                },
            }
            resp = requests.post(**data)
            self.logger.debug("Request URL: {}".format(resp.request.url))
            self.logger.debug('TaaS response status code: {}'.format(resp.status_code))
            if resp.status_code != 201:
                self.logger.error('TaaS API call failed: {}'.format(resp.text))
            else:
                self.logger.info('Response text:{}'.format(resp.text))
        finally:
            shutil.rmtree(tmp_dir_path)

    def send_crft_kafka_notification(self, crft_dir):
        headers = {'Content-Type': 'application/vnd.kafka.json.v1+json'}
        proxies = {"http": None, "https": None}
        notify_api = (
            "https://sjc-ddkafka-rest.ciscointernal.com/topics/s7gtq34f6qn.devx_ng_telemetry_business_pyats_results"
        )
        data = {
            'records': [
                {
                    'value': {
                        'source': 'com.cisco.devx.crft',
                        'event': 'collection',
                        'dataKey': self.db_build_id,
                        'startTime': self.start,
                        'endTime': time.time(),
                        'dataVolume': 'small',
                        'data': {'crft_upload_location': crft_dir},
                    }
                }
            ]
        }
        try:
            req = requests.post(
                url=notify_api, data=json.dumps(data).encode('utf-8'), headers=headers, timeout=15, proxies=proxies
            )
            self.logger.debug("Kafka request URL: {}".format(req.request.url))
            self.logger.debug("Request body: {}".format(req.request.body))
            self.logger.debug("Request headers: {}".format(req.request.headers))
            if req.status_code != 200:
                self.logger.error('Notification API call failed:\n{}'.format(req.text))
            else:
                self.logger.info('Notification API call to {} succeeded.'.format(notify_api))
                self.logger.debug('Status:{}; Text:{}'.format(req.status_code, req.text))

        except Exception:
            self.logger.exception('Failed Kafka notification:')

    def get_cedge_raw_versions(self):
        # Returns full output of `show version` for all cedges
        cedges = [m for m in self.tb.machines() if self.tb.is_cedge(m)]
        raw_versions = {}
        p = []
        q = queue.Queue(len(cedges))
        for machine_name in cedges:
            all_args = (self.ultimate['confd'].get_show_version_raw, (machine_name,), q, machine_name)
            proc = Thread(target=self.call_func_as_process, args=all_args)
            proc.start()
            p.append(proc)
        for proc in p:
            proc.join()
        while q.empty() is False:
            machine_name, result = q.get()
            raw_versions[machine_name] = {'version_raw': result}
        return raw_versions

    def crft_taas_upload(self, crft_files, local_crft_dir, raw_versions):
        crft_remote_base_dir = "/auto/polaris-storage/test-run-data/crft/vtest"
        crft_remote_dir = os.path.join(crft_remote_base_dir, str(self.db_build_id))
        try:
            self.tb.mkpath(crft_remote_dir)
        except Exception:
            self.logger.exception("Failed to create directory at: {}".format(crft_remote_dir))
            return
        for machine_name in crft_files:
            crft_file = crft_files[machine_name][0]
            crft_file_path = os.path.join(local_crft_dir, crft_file)
            shutil.copy(crft_file_path, crft_remote_dir)
        crft_report = self.create_crft_report(crft_remote_dir, crft_files, raw_versions)
        local_crft_yaml = os.path.join(local_crft_dir, 'crft.yaml')
        with open(local_crft_yaml, 'w') as f:
            yaml.safe_dump(crft_report, f)
            shutil.copy(local_crft_yaml, crft_remote_dir)
        self.notify_taas(local_crft_yaml)

    def collect_crft_from_cedge(self, machine, dst):
        crft_file_path = ""
        crft_file_name = ""
        try:
            self.ultimate['confd'].exec_cmd(machine, ['service', 'internal'])
            self.ultimate['iosxe'].check_and_renew_iosxe_session(machine)
            self.ultimate['iosxe'].delete_force_recursive(machine, 'bootflash:CRFT_*')
            output = self.ultimate['confd'].show_cli_cmd(
                machine,
                "request platform software crft collect localhost tag _{}__{}__000001_".format(
                    self.db_build_id, machine
                ),
            )
            match = re.search(r'Successful .* CRFT .* "(/bootflash/CRFT.*\.tar\.gz)"', output)
            if match:
                crft_file_path = match.group(1)
                crft_file_name = os.path.basename(crft_file_path)
                self.logger.info("CRFT - file generated in {}".format(crft_file_path))
                self.tb.copy_from_machine(machine, crft_file_name, dst)
            else:
                self.logger.error("CRFT - Couldn't generate CRFT data on {}: {}".format(machine, output))
                try:
                    node_info = self.dtdash_dict["nodes"][machine]
                except Exception as ex:
                    self.logger.error("CRFT - collect_crft_from_cedge - {}".format(ex))
                else:
                    self.logger.info("CRFT - {} device type: {}".format(machine, node_info.get("node_type", "unknown")))
                    self.logger.info("CRFT - {} is DUT: {}".format(machine, node_info.get("dut", "unknown")))
            self.ultimate['iosxe'].delete_force_recursive(machine, 'bootflash:CRFT_*')
        except Exception:
            self.logger.error("CRFT - Failure during CRFT collection from {}".format(machine), exc_info=True)
            crft_file_name = "Failure during CRFT collection"
        finally:
            return crft_file_name

    def create_crft_report(self, crft_remote_dir, crft_files, raw_versions):
        start_microsec = repr(self.start).split('.')[1]
        report = {
            'job': self.db_test_suite,
            'job_uid': self.db_build_id,
            'name': self.db_test_suite,
            'run_id': self.db_build_id,
            'storage': crft_remote_dir,
            'submitter': 'tester',
            'command_line': 'runner {}'.format(self.args_string),
            'executiontime': int(time.time() - self.start),
            'starttime': time.strftime('%Y-%m-%dT%H:%M:%S.{}%z'.format(start_microsec), time.gmtime(self.start)),
            'overall_result': self.db_test_suite_result,
            'host_name': self.tb_hostname,
            'coverage_type': 'null',
            'execution_type': 'null',
            'coverage_level': "job",
            'test_suite': self.db_test_suite,
            'framework': 'vtest-runner',
            'release': '',
            'request_id': self.db_build_id,
            'suite_id': "VTEST::{}".format(self.db_test_suite),
            'files': crft_files,
            'tasks': [],
            'devices': raw_versions,
            'metadata': {'group_id': 'routing', 'is_sdwan': True},
        }
        return report

    def collect_data_from_cedge(self, machine, dst):
        """
        Collects btrace and debug info from a cedge machine.
        """
        if self.disable_pm_console_logger:
            self.logger.info('Not collecting logs from cEdges because of \'-ncl\'')
            return

        # Make sure we operate in folder as dst, not on full path to file
        if os.path.splitext(dst)[1]:
            dst = os.path.dirname(dst)
        try:
            self.logger.info('Generating admin-tech on %s' % machine)
            admin_tech_dst_path = self.get_cedge_admin_tech(machine, dst)
        except Exception:
            self.logger.info("Failed to collect admin-tech from {}".format(machine), exc_info=True)
        else:
            self.logger.info('{}: unpacking admin-tech {}'.format(machine, admin_tech_dst_path))
            unpack_tar_gz(self.logger, admin_tech_dst_path)
        self.logger.info("TRUE/FALSE MACHINE is DUT: {}".format(self.dtdash_dict['nodes'].get(machine, {}).get('dut')))
        if self.btrace:
            try:
                self.ultimate['iosxe'].check_and_renew_iosxe_session(machine)
                self.ultimate['iosxe'].delete_force_recursive(machine, 'bootflash:BTRACE_*')
                output = self.ultimate['confd'].show_cli_cmd(
                    machine,
                    "request platform software trace archive target bootflash:/BTRACE__{}__{}__000001__".format(
                        self.db_build_id, machine
                    ),
                )
                match = re.search(r'Done with creation of the archive file: \[bootflash:/(BTRACE_.*.tar.gz)\]', output)
                if match:
                    btrace_file_path = match.group(1)
                    self.logger.info("Btrace file generated in {}".format(btrace_file_path))
                    self.tb.copy_from_machine(machine, os.path.basename(btrace_file_path), dst)
                else:
                    self.logger.info("Couldn't generate Btrace")
                self.ultimate['iosxe'].delete_force_recursive(machine, 'bootflash:BTRACE_*')
            except Exception:
                self.logger.warning("Failure during Btrace collection from {}".format(machine), exc_info=True)
        self.collect_cedge_debug_info(machine, dst)

    def log_cert_on_devices(self):
        if not hasattr(self, "dtdash_dict"):
            self.logger.warning("Skipping log_cert_on_devices() as self doesn't contain dtdash_dict")
            return
        duts = cert_validation.get_duts(self.tb, self.dtdash_dict)

        if not duts:
            self.logger.warning("Skipping log_cert_on_devices() as list of duts is epmpty")
            return

        p = []
        q = queue.Queue(len(duts))
        cert_data = {}

        # Start threads
        self.logger.info("Start cert validation on {}".format(duts))
        for machine_name in duts:
            all_args = (
                cert_validation.get_expiry_date,
                (self.tb, self.ultimate, self.dtdash_dict, machine_name),
                q,
                machine_name,
            )
            proc = Thread(target=self.call_func_as_process, args=all_args)
            proc.start()
            p.append(proc)

        # Wait for all threads
        for proc in p:
            proc.join()

        # Collect results
        while q.empty() is False:
            machine_name, result = q.get()
            cert_data[machine_name] = result

        self.logger.info("Cert validation done. Saving results")

        if self.db_write and self.db_build_id:
            try:
                with self.get_db_client() as db_handle:
                    cert_validation.save_results(
                        self.dtdash_dict,
                        self.db_build_id,
                        self.current_suite_name,
                        self.tb_hostname,
                        cert_data,
                        db_handle,
                    )
            except Exception as ex:
                self.logger.error(
                    "Cert validation results : saving into db failed: {}\n Trying to save in dtdash.json".format(ex)
                )
                cert_validation.save_results(
                    self.dtdash_dict,
                    self.db_build_id,
                    self.current_suite_name,
                    self.tb_hostname,
                    cert_data,
                )
        else:
            self.logger.info("Cert validation results : This run is not using DB, saving in dtdash.json")
            cert_validation.save_results(
                self.dtdash_dict,
                self.db_build_id,
                self.current_suite_name,
                self.tb_hostname,
                cert_data,
            )

    def collect_cedge_debug_info(self, machine, dst):
        try:
            self.ultimate['iosxe'].check_and_renew_iosxe_session(machine)
            self.logger.info('Collecting debug info from %s' % machine)
            self.logger.info('Deleting {} bootflash:vtestdebug folder if any'.format(machine))
            self.ultimate['iosxe'].delete_force_recursive(machine, 'bootflash:vtestdebug')
            self.ultimate['iosxe'].mkdir(machine, 'bootflash:vtestdebug')
            self.ultimate['iosxe'].mkdir(machine, 'bootflash:vtestdebug/memory')
            self.ultimate['iosxe'].mkdir(machine, 'bootflash:vtestdebug/lsan')
            self.logger.info('memaudit -v > /bootflash/vtestdebug/memory/memaudit-log.txt')
            self.ultimate['iosxe'].exec_cmd_in_binos(machine, 'cp -r /bootflash/syslog /bootflash/vtestdebug/', timeout=180)
            self.ultimate['iosxe'].exec_cmd_in_binos(machine, 'memaudit -v > /bootflash/vtestdebug/memory/memaudit-log.txt', timeout=180)
            self.logger.info('lsmod > /bootflash/vtestdebug/memory/lsmod.txt')
            self.ultimate['iosxe'].exec_cmd_in_binos(machine, 'lsmod > /bootflash/vtestdebug/memory/lsmod.txt')
            self.logger.info('journalctl -a > /bootflash/vtestdebug/vdebug.log')
            self.ultimate['iosxe'].exec_cmd_in_binos(machine, 'journalctl -a > /bootflash/vtestdebug/vdebug.log', timeout=180)
            if self.cflow_coverage:
                self.ultimate['iosxe'].collect_cflow_coverage_data(machine)
                if self.check_instrumented_cedge_image(machine):
                    self.ultimate['iosxe'].exec_cmd_in_binos(machine, '/usr/bin/cflow dump', timeout=600)
                self.ultimate['iosxe'].exec_cmd_in_binos(machine, 'mv /bootflash/cflow /bootflash/vtestdebug/', timeout=180)
            try:
                self.ultimate['iosxe'].collect_lsan_data(machine, 'bootflash:vtestdebug/lsan')
            except Exception as ex:
                self.logger.warning('Failed to collect lsan data. {}'.format(ex))
            self.ultimate['iosxe'].collect_memory_debug_info(machine, 'bootflash:vtestdebug/memory')
            self.logger.info('Collected memory debug info')
            self.logger.info('Copying audit logs from  %s' % machine)
            self.ultimate['iosxe'].exec_cmd_in_binos(machine, 'cp -r /var/log/audit /bootflash/vtestdebug/', timeout=180)
        except Exception:
            self.logger.warning('Script failed collecting debug logs on {}'.format(machine), exc_info=True)
        finally:
            vtestdebug_dst_path = None
            try:
                self.logger.info('Archiving collected debug info')
                self.ultimate['iosxe'].exec_cmd_in_binos(machine, 'tar -czf /bootflash/vtestdebug.tar.gz /bootflash/vtestdebug', timeout=180)
                self.logger.info('Copying {}:vtestdebug.tar.gz to: {}'.format(machine, dst))
                self.tb.copy_from_machine(machine, 'vtestdebug.tar.gz', dst)
                vtestdebug_dst_path = os.path.join(dst, 'vtestdebug.tar.gz')
                subprocess.call('tar -xf %s -C %s --warning=no-timestamp' % (vtestdebug_dst_path, dst), shell = True)
            except Exception:
                self.logger.exception('Failed collecting debug info for {}'.format(machine))
            finally:
                subprocess.call('rm -f %s' % vtestdebug_dst_path, shell = True)
                self.ultimate['iosxe'].delete_force_recursive(machine, 'bootflash:vtestdebug')
                self.ultimate['iosxe'].delete_force_recursive(machine, 'bootflash:vtestdebug.tar.gz')

    def get_cedge_admin_tech(self, machine, dst):
        self.logger.info('Generating admin-tech on %s' % machine)
        session = self.tb.get_machine_session(machine, MACHINE_SESSION_PEXPECT_TIMEOUT)
        sessions = {'confd': {machine: session}}
        confd_session = CONFDSession(self.tb, sessions, self.logger)
        admin_tech_src_path = None
        try:
            res = confd_session.request_admin_tech_cedge(machine, expect_timeout=900)
            if res[0]:
                admin_tech_src_path = res[1]
                self.tb.copy_from_machine(machine, admin_tech_src_path.split('bootflash:')[1], dst)
                self.logger.info('Admin-tech copied to {}. '.format(dst))
                return os.path.join(dst, os.path.basename(admin_tech_src_path))
        except Exception:
            self.logger.exception('Failed to collect admin-tech from {}'.format(machine))
        finally:
            if admin_tech_src_path:
                self.logger.info('Deleting admin-tech path {} from {}. '.format(admin_tech_src_path, machine))
                self.ultimate['iosxe'].delete_force_recursive(machine, admin_tech_src_path)
            if session and session.isalive():
                session.close()

    def get_admin_tech(self, machine, dst):
        """
        Get admin-tech from the specified machine and scp it to dst
        dst should be the complete path + name of the destination
        """
        #skip the admin tech collection from UCS/CSP/NFVIS
        if self.tb.is_nfvis(machine):
            return 0

        confd = self.confd
        session = confd.sessions['confd'][machine]
        if session and session.isalive():
            try:
                confd.config_mode_abort(machine)
            except OSError:
                session.close()
        if not session or session.isalive() is False:
            logfile = session.logfile if session else None
            session = self.tb.get_machine_session(machine, MACHINE_SESSION_PEXPECT_TIMEOUT, logfile, False, True, False)
            confd.sessions['confd'][machine] = session
        session.timeout = 300
        try:
            res = confd.request_admin_tech(machine)
            if res[0] is False:
                self.logger.warning(res[1])
                return 1

            admin_tech_src_path = res[1]
            self.logger.info("{}: Generated {}".format(machine, admin_tech_src_path))
            admin_techs = confd.request_admin_tech_list(machine)
            self.logger.info("{}: admin-tech list: {}".format(machine, admin_techs))
            try:
                self.tb.copy_from_machine(machine, admin_tech_src_path, dst)
            except Exception:
                self.logger.warning(
                    "{}: Failed to copy admin-tech {}".format(machine, admin_tech_src_path), exc_info=True
                )
            else:
                self.logger.info('{}: unpacking admin-tech {}'.format(machine, dst))
                unpack_tar_gz(self.logger, dst)
        except pexpect.TIMEOUT:
            confd_log = session.logfile
            session.close()
            session = self.tb.get_machine_session(
                machine, MACHINE_SESSION_PEXPECT_TIMEOUT, confd_log, False, True, False
            )
            confd.sessions['confd'][machine] = session
            self.logger.error('Could not generate admin-tech on %s. Please check to make sure there aren\'t too many core files in /var/crash. Copying out /var/log instead' % machine)
            src = '/var/log/*'
            dst1 = os.path.join(dst, 'var', 'log')
            self.tb.mkpath(dst1)
            result = self.tb.scp_from_machine(machine, src, dst1, True, True, False, 180)
            if result[0] is False:
                self.logger.warning('scp failed from %s: %s' % (machine, result[1]))
                return 1
        return 0

    def print_func_name_to_logs(self, mch, name, arguments=None, subtest=False):
        if mch not in self.sessions['root']:
            if type(mch) == str and (
                mch
                in [
                    'All',
                    'SPIRENT',
                    'TestBedHost',
                    'Protractor',
                    'HTTP',
                    'LANDSLIDE',
                    'VMANAGE_HTTP_SERVER',
                    'JMETER',
                    'NA',
                    'IXIA',
                ]
            ):
                pass
            elif mch in self.vmanage_ips:
                pass
            else:
                if not self.ultimate.get('suppress_missing_node_msg', [False])[0]:
                    self.logger.warning('%s is not one of the nodes, assuming you know what you are doing' % mch)
        else:
            pass

    def get_all_scripts(self):
        """Retrieves all scripts (test suites) that are located in the script directory"""
        protocols = []
        prefix = 'test_'
        for item in (Path(self.tests_dir) / 'scripts').glob('*.ttf'):
            if item.stem.startswith(prefix):
                protocols.append(item.stem[len(prefix) :])
        protocols += self.get_suite_combinations()
        protocols.remove('sanity')
        return protocols

    def get_suite_documenation(self, suite_name):
        """This function is used to get the documentation suite for the suites
        TODO: Needs update as TTF parsing is moved to tests/lib/ttf_parser.py
        """
        doc_header = "\n\nHelp on TestSuite %s:\n\nNAME\n    %s\n\n" % (suite_name, suite_name)
        #suite_name already validated in runner arp parser. suite_name cannot be invalid name
        file_path = f'{self.tests_dir}/scripts/test_{suite_name}.ttf'
        #doc_header += "FILE\n    %s\n\n" % (file_path)
        try:
            #Open the ttf file and read contents
            f = open(file_path, 'r')
            file_content = f.read()
            f.close()
        except IOError as err:
            doc_header += "Cannot load %s file\n%s\n" % (file_path, err)
            return doc_header

        # Since ttf file is plain text file, write a parsing logic
        # to extract the document string
        # Document string is expected to be within """ quotes
        triple_quote_start = False
        modules_dict = {}
        doc_string = "DESCRIPTION\n"
        mod_string = "MODULES\n"
        func_header = "FUNCTIONS\n"
        tcase_string = ""
        modules = ""
        for lines in file_content.splitlines():
            re_triple_quotes = re.findall(r'"""', lines)
            re_modules = re.findall(r"modules.*=.*\[('.*')*\]", lines)
            re_testcase = re.findall(r'(^\s*(%s)[ ]*-[ ]*((test.*)[ ]*=[ ]*(\[.*\])))' % ('|'.join(modules)), lines)
            if re_modules != []:
                # Get the modules
                modules = misc.list_from_string_repr(re_modules[0])
                mod_string += "    %s\n\n" % ", ".join(modules)
                for module in modules:
                    # import the modules to extract testcase docs
                    modules_dict[module] = import_module(module)
            if triple_quote_start is False and re_triple_quotes != []:
                if len(re_triple_quotes) == 2:
                    # Handle single line doc Ex: """ String """
                    doc_line = (re.findall(r'"""(.*)"""', lines))
                    doc_string += "    %s\n" % doc_line[0]
                    continue
                # Find the start of the document string which is first occurence of """"
                triple_quote_start = True
                first_line = (re.findall(r'"""(.*)', lines))
                # If """ line has doc string, extract the doc string
                if len(first_line) == 1 and first_line != ['']:
                    doc_string += "    %s\n" % first_line[0]
                # Start extracting the doc string
            elif re_triple_quotes != []:
                #Find the end of the document string which is next occurence of """"
                last_line = (re.findall(r'(.*)"""', lines))
                # If """ line has doc string, extract the doc string
                if len(last_line) == 1:
                    doc_string += "    %s\n" % last_line[0]
                # Stop extracting the doc string
                triple_quote_start = False
            # Extracting lines between """ quotes
            elif triple_quote_start:
                doc_string += "    %s\n" % lines
            elif re_testcase != []:
                # Handle testcases
                t_module = re_testcase[0][1].strip()
                t_name   = re_testcase[0][3].strip()
                t_ref = modules_dict[t_module].__dict__[t_name]
                t_doc = t_ref.__doc__
                if t_doc is not None:
                    t_doc_list = t_doc.splitlines()
                    t_doc = "\n    ".join(t_doc_list)
                    tcase_string += "    %s.%s()\n        %s\n" % (t_module, t_name, t_doc)
                else:
                    tcase_string += "    %s.%s()\n\n" % (t_module, t_name)

        final_doc = doc_header + mod_string + doc_string + func_header +tcase_string
        return final_doc

    def get_suite_combinations(self, name = None, value = 0):
        """Retrieves all suite combinations that are defined in the pref yaml file"""
        ret = []
        if name is None:
            try:
                ret += list(pref['suites'].keys())
            except KeyError:
                pass
        else:
            try:
                suite_entry = pref['suites'][name]
                if self.tb.hw and 'hw' in list(suite_entry.keys()):
                    suite_entry = pref['suites'][name]['hw']
                if self.tb_hostname in list(suite_entry.keys()):
                    suite_entry = pref['suites'][name][self.tb_hostname]
                if value == 0:
                    ret += suite_entry['protocols']
                elif value == 1:
                    ret += suite_entry['tags']
                else:
                    ret += suite_entry['level']
            except KeyError:
                self.logger.error('ERROR: The specified suite combination is not defined')
        return ret

    def get_all_tags(self, tags, suite_name):
        if len(tags) > 0:
            tags.append('default')
        else:
            if suite_name in self.get_suite_combinations():
                tags = self.get_suite_combinations(suite_name, 1)
        return tags

    def check_func_level(self, func_tags):
        if re.match(r'[pP]([0-9])$', self.level):
            levels = {'P%d' % x for x in range(10)}
            uppercase_func_tags = set(map(lambda x: x.upper(), func_tags))
            matching_tags = levels & uppercase_func_tags
            if matching_tags:
                return min(matching_tags) <= self.level.upper()
            else:
                return True
        try:
            levels = pref['levels']
        except KeyError:
            self.logger.error('ERROR: No test levels specified in the preference.yaml file')
            return False
        try:
            current_levels_index = levels.index(self.level)
        except ValueError:
            self.logger.error('WARNING: The specified level does not exist')
            return False
        func_level = self.get_level(func_tags)
        if func_level == -1:
            return False
        if current_levels_index >= func_level:
            return True
        else:
            return False

    def get_level(self, func_tags):
        """
        """

        try:
            levels = pref['levels']
        except KeyError:
            err = 'No default test level specified in the preference file'
            self.logger.error(err)
            return -1
        intersection = set(func_tags) & set(levels)
        index = -1
        while len(intersection) > 0:
            level_entry = intersection.pop()
            temp_index = levels.index(level_entry)
            if temp_index >= index:
                index = temp_index
        if index == -1:
            try:
                return levels.index(pref['default_level'])
            except KeyError:
                err = 'No default test level specified in the preference file'
                self.logger.error(err)
                return -1
        else:
            return index

    def compare_configs(self, older_configs, file_name=None):
        """
        Compares the current configs to the older_configs, provided as an
        argument, and returns all the differences.

        @params
          older_configs: a dictionry containing older configs for a set of nodes

        @return
          A list containing machine_name, diff pair
        """

        diffs = []
        current = self.get_all_configs(file_name=file_name)
        for machine in older_configs:
            if machine not in current:
                diffs.append((machine, 'Could not retrieve current configs'))
                continue
            # TODO: for some reason compared config contains timestamp in last line.
            # This makes check below (as well as diff) incorrectly marked as different.
            if older_configs[machine] != current[machine]:
                diff_gen = difflib.unified_diff(
                    older_configs[machine].splitlines(True),
                    current[machine].splitlines(True),
                    fromfile="{}_old_cfg".format(machine),
                    tofile="{}_curr_cfg".format(machine),
                )
                diff_str = "".join(diff_gen)
                diff_pair = (machine, "\n".join(["Unified diff:", diff_str, ""]))
                diffs.append(diff_pair)
        return diffs

    def get_all_configs(self, file_name=None):
        """
        Gets the running config from all the nodes in the testbed and stores
        them in a dictionary. This function can only be called once the
        ultimate dictionary has been created. We use this function to store
        configs for the purpose of config diffs. For more info: Look at
        "def compare_configs".
        """
        configs = {}
        if self.skip_comparing_of_configs is not None:
            excluded_devices = self.skip_comparing_of_configs
        else:
            excluded_devices = pref.get('skip_comparing_of_configs', [])
        p = []
        q = queue.Queue(len(self.tb.machines()))
        for machine in self.tb.machines():
            if machine not in excluded_devices and not self.tb.is_ucs(machine) and not self.tb.is_highrise(machine):
                if self.tb.is_cedge(machine):
                    cmd = 'show sdwan running-config'
                else:
                    cmd = 'show running-config'
                confd = self.ultimate['confd']
                func_args = (machine, cmd, -1, True)
                all_args = (confd.show_cli_cmd, func_args, q, machine)
                proc = Thread(target=self.call_func_as_process, args=all_args)
                proc.name = machine
                proc.start()
                p.append(proc)
        #Wait for all the threads to get done
        failed = []
        for proc in p:
            if len(failed) == 0:
                proc.join(300)
            if proc.isAlive():
                failed.append(proc.name)
        #Get the results from the queue
        while q.empty() is False:
            machine, res = q.get()
            configs[machine] = res
            if file_name:
                machine_log_path = os.path.join(self.logs_sub_dir, machine)
                file_path = os.path.join(machine_log_path, '{}-{}.log'.format(machine, file_name))
                file_handle = open(file_path, 'a+')
                file_handle.write(res)
        for machine in failed:
            configs[machine] = ""
        if len(failed) > 0:
            self.logger.warning("Could not get configs for %s" % failed)
        return configs

    def get_testbed_ip_addr(self, tb_name):
        """
        Returns the ip address for the specified testbed. This is used as a
        backup for DNS
        """

        testbeds = pref['testbeds']
        try:
            ip = testbeds[tb_name]['ip']
        except KeyError:
            ip = None
        return ip

    def get_all_sessions_for_a_machine(self, machine, set_sessions=False):
        """
        Creates a cli and root session for the specified machine. This function
        can also update the current global sessions

        @param
          set_sessions: if true then the newly created sessions replace the
          original sessions in the global session containers(dictionaries)

        @return
          sessions: if set_sessions is false then a regular cli session and a
          root session for the specified machine are returned
        """

        p = []
        q = queue.Queue(len(self.tb.machines()) * 2)
        #Create a pexpect session in the cli and put it in the queue
        func_args = (machine, MACHINE_SESSION_PEXPECT_TIMEOUT, None, False, True, False)
        all_args = (self.tb.get_machine_session, func_args, q, machine)
        proc = Thread(target = self.call_func_as_process, args = all_args)
        proc.start()
        p.append(proc)
        #Create a pexpect session in the bash shell, this logs in as root, and
        #put it in the queue
        if self.tb.personality(machine) == 'vmanage':
            ret_name = '%s-ncs' % machine
            func_args = (machine, MACHINE_SESSION_PEXPECT_TIMEOUT, None, False, True, False, True, True)
            all_args = (self.tb.get_machine_session, func_args, q, ret_name)
            proc = Thread(target = self.call_func_as_process, args = all_args)
            proc.start()
            p.append(proc)
        #Create a pexpect session in the bash shell, this logs in as root, and
        #put it in the queue
        ret_name = '%s-root' % machine
        func_args = (machine, MACHINE_SESSION_PEXPECT_TIMEOUT, None, False, True, True)
        all_args = (self.tb.get_machine_session, func_args, q, ret_name)
        proc = Thread(target = self.call_func_as_process, args = all_args)
        proc.start()
        p.append(proc)

        #if machine is cEdge get iosxe session
        if self.tb.is_cedge(machine):
            ret_name = '%s-iosxe' % machine
            func_args = (machine, MACHINE_SESSION_PEXPECT_TIMEOUT, None)
            all_args = (self.tb.get_iosxe_cli_session, func_args, q, ret_name)
            proc = Thread(target = self.call_func_as_process, args = all_args)
            proc.start()
            p.append(proc)

        #Wait for all the threads to get done
        for proc in p:
            proc.join()
        errors = 1
        #Get the sessions from the queue
        while q.empty() is False:
            mch, session = q.get()
            if session == -99:
                errors += 1
                continue
            if 'root' in mch:
                root_session = session
            elif 'ncs' in mch:
                ncs_session = session
            elif 'iosxe' in mch:
                iosxe_session = session
            else:
                reg_session = session
            errors = 0
        if set_sessions is False:
            if errors > 0:
                return None, None, None, None
            else:
                return reg_session, root_session, ncs_session, iosxe_session
        else:
            if errors > 0:
                return False
            try:
                confd = self.ultimate['confd']
                if confd.sessions['confd'][machine].logfile != sys.stdout:
                    confd.sessions['confd'][machine].logfile.close()
                if confd.sessions['root'][machine].logfile != sys.stdout:
                    confd.sessions['root'][machine].logfile.close()

                reg_session.logfile = open(confd.sessions['confd'][machine].logfile.name, 'a+')
                root_session.logfile = open(confd.sessions['root'][machine].logfile.name, 'a+')

                confd.sessions['confd'][machine].terminated = True
                confd.sessions['root'][machine].terminated = True
                confd.sessions['confd'][machine] = reg_session
                confd.sessions['root'][machine] = root_session

            except (AttributeError, UnboundLocalError):
                pass
            except KeyError:
                confd.sessions['confd'][machine] = reg_session
                confd.sessions['root'][machine] = root_session
            if self.tb.personality(machine) == 'vmanage':
                try:
                    if confd.sessions['ncs'][machine].logfile != sys.stdout:
                        confd.sessions['ncs'][machine].logfile.close()
                    ncs_session.logfile = open(confd.sessions['ncs'][machine].logfile.name, 'a+')
                    confd.sessions['ncs'][machine].terminated = True
                    confd.sessions['ncs'][machine] = ncs_session
                except KeyError:
                    confd.sessions['ncs'][machine] = ncs_session
            if self.tb.is_cedge(machine):
                try:
                    if confd.sessions['iosxe'][machine].logfile !=sys.stdout:
                        confd.sessions['iosxe'][machine].logfile.close()
                    iosxe_session.logfile = open(confd.sessions['iosxe'][machine].logfile.name, 'a+')
                    confd.sessions['iosxe'][machine].terminated = True
                    confd.sessions['iosxe'][machine] = iosxe_session
                except KeyError:
                    confd.sessions['iosxe'][machine] = iosxe_session
            return True

    def check_suite_support(self, hostname, suite):
        """
        Checks if the specified suite is supported on the specified testbed
        This information is present in the preference file
        """
        if hostname in pref['testbeds']:
            if 'suites_not_supported' in pref['testbeds'][hostname] and 'suites_supported' in pref['testbeds'][hostname]:
                #Testbed cannot have both the list. Define either supported_list or unsupported list, not both
                self.logger.error('Testbed definition error in preference yaml. Define either supported_list or unsupported list, not both')
                return 1
            if 'suites_not_supported' in pref['testbeds'][hostname] and suite in pref['testbeds'][hostname]['suites_not_supported']:
                err = '%s suite is not supported on this testbed' % suite
                self.logger.error(err)
                msg = 'List of suites not supported on this testbed: %s' % pref['testbeds'][hostname]['suites_not_supported']
                self.logger.warning(msg)
                self.logger.warning('Check testbed status page for supported testbeds for your suite, and resubmit your run')
                return 1
            if 'suites_supported' in pref['testbeds'][hostname] and suite not in pref['testbeds'][hostname]['suites_supported']:
                err = '%s suite is not supported on this testbed' % suite
                self.logger.error(err)
                msg = 'List of suites supported on this testbed: %s' % pref['testbeds'][hostname]['suites_supported']
                self.logger.error(msg)
                self.logger.error('Check testbed status page for supported testbeds for your suite, and resubmit your run')
                return 1
        return 0

    def check_branch_support(self, hostname, branch):
        """
        Checks if the specified branch is supported on the specified testbed
        This information is present in the preference file
        """
        #Allow regressions to run on any non-master testbeds, if -evm is specified
        if hostname not in ['testbed3', 'testbed13'] and self.exclude_vmanage:
            return 0
        if hostname in pref['testbeds']:
            if 'branch_not_supported' in pref['testbeds'][hostname] and 'branch_supported' in pref['testbeds'][hostname]:
                #Testbed cannot have both the list. Define either supported_list or unsupported list, not both
                self.logger.error('Testbed definition error in preference yaml. Define either supported_list or unsupported list, not both')
                return 1
            if 'branch_not_supported' in pref['testbeds'][hostname] and branch in pref['testbeds'][hostname]['branch_not_supported']:
                err = '%s branch is not supported on this testbed' % branch
                self.logger.error(err)
                msg = 'List of branches not supported on this testbed: %s' % pref['testbeds'][hostname]['branch_not_supported']
                self.logger.error(msg)
                self.logger.error('Check testbed status page for supported testbeds for your branch, and resubmit your run')
                return 1
            if 'branch_supported' in pref['testbeds'][hostname] and branch not in pref['testbeds'][hostname]['branch_supported']:
                err = '%s branch is not supported on this testbed' % branch
                self.logger.error(err)
                msg = 'List of branches supported on this testbed: %s' % pref['testbeds'][hostname]['branch_supported']
                self.logger.error(msg)
                self.logger.error('Check testbed status page for supported testbeds for your branch, and resubmit your run')
                return 1
        return 0

    def save_current_configs(self, config_name, remote_ip=None):
        """
        Saves the current state of all the nodes.

        For each and every node saves the current config and copies
        it out to the specified dir.

        @params
          - config_name: the name of the directory where we want to
            copy the current configs. The final loc is
            $VTEST/tests/scripts/"config_name"
        """

        dir_path = os.path.join(os.path.dirname(__file__), 'scripts')
        dir_path = os.path.join(dir_path, 'setup_configs')
        dir_path = os.path.join(dir_path, os.path.basename(config_name))
        testbed = self.get_testbed()
        if testbed is None:
            self.logger.error('No testbed is up')
            return 1
        self.tb = HyperVisor(testbed, self.debug, log_root=self.logs_sub_dir)
        res = self.tb.get_all_mchs_sessions()
        if res == -99:
            return res
        confd_machine_sessions = res
        confd = CONFDSession(self.tb, {'confd': confd_machine_sessions}, False, None)
        self.ultimate = {}
        self.ultimate['confd'] = confd
        self.ultimate['sessions'] = {'confd': confd_machine_sessions}
        try:
            os.mkdir(dir_path)
        except OSError:
            pass
        res = self.save_configs(dir_path, remote_ip=remote_ip)
        for machine in self.tb.machines():
            self.close_session(machine)
        del self.ultimate
        return res

    def save_configs(self, loc=None, config_name=None, confd=None, remote_ip=None):
        """
        Saves configs on all the nodes and then, optionally, copy them out.

        This function calls the save_and_copy_config function on all the
        nodes, the calls are made as sperate threads to make the function
        faster.

        Reason for faster configs is because "Slow configs are no configs"
        (please read this in the appropriate voice, from the link),
        http://www.youtube.com/watch?v=Buf4_Crt27c!
        """

        fail = 0
        p = []
        q = queue.Queue(len(self.tb.machines()))
        for machine in self.tb.machines():
            if self.tb.is_highrise(machine):
                continue
            func_args = (machine, loc, config_name, confd, remote_ip)
            all_args = (self.save_and_copy_config, func_args, q)
            proc = Thread(target = self.call_func_as_process, args = all_args)
            proc.start()
            p.append(proc)
        #Wait for all the threads to get done
        for proc in p:
            proc.join()
        while q.empty() is False:
            res = q.get()
            if not res[0]:
                self.logger.error(res[1])
                fail += 1
        return fail




    def save_and_copy_config(self, machine, loc=None, config=None, confd=None, remote_ip=None):
        """
        Saves the configs on a particular node and then, optionally,
        copy it out.

        @params
            - If loc is None, then we will not copy out the saved configs,
              else they
              will be copied out to the loc dir
            - If config_name is None, then use a default name
            - If confd is None, then use confd from the ultimate dictionary
        """

        if config is None:
            config = '/home/admin/%s_config' % machine
        else:
            config = '/home/admin/%s_%s' % (machine, config)
        if confd is None:
            confd = self.ultimate['confd']
        res = confd.save_config(machine, config)
        if res[0]:
            if loc is not None:
                if remote_ip is not None:
                    res = self.tb.scp_from_machine_with_ip(machine, remote_ip, config, loc)
                else:
                    res = self.tb.scp_from_machine(machine, config, loc)
                if not res[0]:
                    err_msg = 'Could not scp out the config for %s' % machine
                    err_msg += ', %s' % res[1]
                    return [False, err_msg]
        else:
            return [False, 'Could not save config for %s' % machine]
        return [True, '']




    def load_specified_configs(self, config_name, remote_ip=None):
        """
        Loads configs on to all the nodes.

        For each and every node load the respective config from the
        specified dir

        @params
          - config_name: the name of the directory where the configs
            are located. The final loc is
            $VTEST/tests/scripts/"config_name"
        """

        dir_path = os.path.join(os.path.dirname(__file__), 'scripts')
        dir_path = os.path.join(dir_path, 'setup_configs')
        dir_path = os.path.join(dir_path, os.path.basename(config_name))
        testbed = self.get_testbed()
        if testbed is None:
            self.logger.error('No testbed is up')
            return 1
        self.tb = HyperVisor(testbed, self.debug, log_root=self.logs_sub_dir)
        res = self.tb.get_all_mchs_sessions()
        if res == -99:
            return res
        confd_machine_sessions = res
        confd = CONFDSession(self.tb, {'confd': confd_machine_sessions}, False, None)
        self.ultimate = {}
        self.ultimate['confd'] = confd
        self.ultimate['sessions'] = {'confd': confd_machine_sessions}
        res = self.load_all_configs(dir_path, remote_ip=remote_ip)
        for machine in self.tb.machines():
            self.close_session(machine)
        del self.ultimate
        return res




    def load_all_configs(self, loc=None, config_name=None, confd=None, remote_ip=None):
        """
        Loads configs on all the nodes. The configs can be copied on to the
        nodes from outside and then loaded or they could be present on the
        nodes from the start.

        This function calls the load_config_on_mch function on all the
        nodes, the calls are made as sperate threads to make the function
        faster.

        Reason for faster configs is because "Slow configs are no configs",
        (please read this in the appropriate voice, from the link)
        http://www.youtube.com/watch?v=Buf4_Crt27c!

        @params
            For an explanation of the args please look at the load_config_on_mch
            function
        """

        fail = 0
        p = []
        q = queue.Queue(len(self.tb.machines()))
        for machine in self.tb.machines():
            if self.tb.is_highrise(machine):
                continue
            func_args = (machine, loc, config_name, confd, remote_ip)
            all_args = (self.load_config_on_mch, func_args, q)
            proc = Thread(target = self.call_func_as_process, args = all_args)
            proc.start()
            p.append(proc)
        #Wait for all the threads to get done
        for proc in p:
            proc.join()
        while q.empty() is False:
            res = q.get()
            if not res[0]:
                self.logger.error(res[1])
                fail += 1
        return fail




    def load_config_on_mch(self, machine, loc=None, config=None, confd=None, remote_ip=None):
        """
        :oads the configs on a particular node. The configs can be copied on
        to the node from outside and then loaded or they could be present on
        the node from the begining.

        @params
            - If loc is None, then the config is located on the node,
              else it will be copied from somewhere outside
            - If config_name is None, then use a default name
            - If confd is None, then use confd from the ultimate dictionary
        """
        if self.tb.is_aws_machine(machine):
            # skip load config on aws machines for now
            return [True, '']

        if config is None:
            config = '/home/admin/%s_config' % machine
        else:
            config = '/home/admin/%s_%s' % (machine, config)
        if loc is not None:
            if not os.path.exists(loc):
                err_msg = 'No such file %s' % loc
                return [False, err_msg]
            loc = os.path.join(loc, os.path.basename(config))
            if remote_ip is not None:
                res = self.tb.scp_from_machine_with_ip(machine, remote_ip, loc, config, to_machine=True)
            else:
                res = self.tb.scp_from_machine(machine, loc, config, to_machine=True)
            if not res[0]:
                err_msg = 'Could not scp the config to %s' % machine
                err_msg += ', %s' % res[1]
                return [False, err_msg]
            self.tb.call(machine, 'chown admin:admin %s' % config, root = True)
        if confd is None:
            confd = self.ultimate['confd']
        res = confd.load_config(machine, 'override', config)
        if not res[0]:
            return [False, 'Could not load config for %s' % machine]
        return [True, '']

    def update_stable_link(self):
        if self.suite in ['express', 'vexpress']:
            self.update_stable_next()
        elif self.suite in ['nExpress', 'nExpress_clouddock']:
            self.update_stable_nms()

    def update_stable_nms(self):
        """
        Updates the stable link on the ftp server.
        """
        versions = self.vmanage_versions
        if len(versions) == 1:
            if self.tb_hostname == 'vip-testbed197':
                version = versions.pop()
                branch = version[0]
                image_version = version[1]
                shell_cmd = 'ssh -o StrictHostKeyChecking=no '
                shell_cmd += '-o UserKnownHostsFile=/dev/null '
                shell_cmd += '-o LogLevel=QUIET '
                shell_cmd += '-l bamboo vip-dmzftp01 "~/ci/update_stable_nms {} {} {}"'.format(
                    self.db_build_id, branch, image_version
                )

                child = pexpect.spawn(shell_cmd)
                index = child.expect(['created', 'Failed'], timeout = 5)
                if index == 0:
                    self.logger.info('Updated the NMS STABLE link to %s' % image_version)
                else:
                    self.logger.info('Could not update NMS STABLE. Check logs at ftp://vip-dmzftp01.cisco.com/ci/update_stable_nms.log')
                return 0
        else:
            err_str = 'Could not update STABLE due to a version mismatch'
            self.logger.error(err_str)
            return 1

    def update_stable_next(self):
        """
        Updates the stable link on the ftp server.
        """
        versions = self.non_vmanage_versions
        if len(versions) == 1:
            if self.tb_hostname == 'vip-testbed197':
                version = versions.pop()
                branch = version[0]
                image_version = version[1]
                shell_cmd = 'ssh -o StrictHostKeyChecking=no '
                shell_cmd += '-o UserKnownHostsFile=/dev/null '
                shell_cmd += '-o LogLevel=QUIET '
                shell_cmd += '-l bamboo vip-dmzftp01 "~/ci/update_stable_next {} {} {}"'.format(
                    self.db_build_id, branch, image_version
                )

                child = pexpect.spawn(shell_cmd)
                index = child.expect(['created', 'Failed'], timeout = 5)
                if index == 0:
                    self.logger.info('Updated the STABLE link to %s' % image_version)
                else:
                    self.logger.info('Could not update STABLE. Check logs at ftp://vip-dmzftp01.cisco.com/ci/update_stable_next.log')
                return 0
        else:
            err_str = 'Could not update STABLE due to a version mismatch'
            self.logger.error(err_str)
            return 1

    def send_results_to_spark(self, room_id='test-cisco-spark-hooks'):
        """Send the results to spark room"""
        spark_session = Spark(SPARK_BOT_TOKEN)
        output = io.StringIO()
        output.write('*Sent by* **%s** [%s]\n' % (self.tb_hostname, self.ip))
        output.write(' > Results for **%s** run on **%s** \n' % (self.suite, self.tb_hostname))
        output.write(
            " - *Run Description:* **%s** \n - *Link to run log:* **%s** \n - *Link to regressdb:* **%s** \n - *Build No:* **%s** \n - *Executed on:* **%s** \n - *Crash Found:* **%s** \n"
            % (self.args_string, self.run_log, self.db_url, self.db_build, self.db_search_date, self.db_core_found)
        )
        output.write(
            " - *Total Tests:* **%s** , *Total Failed Tests:* **%s** \n" % (self.results.executed, self.results.failed)
        )
        output.write(
            " - *Total Sub Tests:* **%s** , *Total Failed Sub Tests:* **%s** \n"
            % (self.results.total_subtests, self.results.failed_subtests)
        )
        seconds = int(time.time() - self.start)
        output.write(" - *Script Run time:* **%s** \n\n" % (str(datetime.timedelta(seconds=seconds))))
        try:
            percentage_pass = (
                old_div(float(self.number_of_tests - self.number_of_failed_tests), float(self.number_of_tests))
            ) * 100
        except Exception:
            percentage_pass = 0.0
            pass
        output.write(" - *Percentage Pass:*  **%s** \n\n" % (str(percentage_pass)))
        data = output.getvalue()
        output.close()
        return spark_session.send_message_to_room(room_id, data)

    def check_errors_in_logs_files(self, error):
        """Check specific errors in logs files and print them, errors can be chcked based on regex or on a string"""
        q = multiprocessing.Queue(len(self.tb.machines()))
        p = []
        for machine in self.tb.machines():
            proc = multiprocessing.Process(target = self.call_func_as_process, args = (self.check_and_get_log_errors_in_machines, (machine,), q))
            proc.start()
            p.append(proc)
        for proc in p:
            proc.join()
        return 0

    def check_and_get_log_errors_in_machines(self, machine):
        """
        1. Here log file is dictionary with error to check on and corresponding error pattern
        2. logfile = {'vconfd': 'oSError*', 'vdebug': 'error'}
        :param machine:
        :return: True
        """
        if self.tb.is_cedge(machine) or self.tb.is_ucs(machine):
            #TODO: Check with Achar, Rauf
            return True
        logfile = {'/var/log/vconfd': 'osCommand error'}
        result = self.tb.check_erros_in_log_files(machine, logfile)
        if result[0]:
            for logfilename in result[1]:
                error = result[1][logfilename]
                if error:
                    self.logger.error('[%s]: logfile [%s] Err [%s] '%(machine, logfilename, error))
        return True

    def check_utd_ssl_support(self, feature='utd'):
        """
        Function to check whether UTD and SSL is supported in hardware
        Checking image variable under pm5 and also check if image start words if local image used in yaml
        :param feature:
        :return: False
        """
        try:
            hw_cedge = 'pm5'
            machines_list=self.tb.machines()
            if hw_cedge in machines_list:
                if machines_list[hw_cedge]:
                    # Check through inventory PID
                    if self.security_pid=='':
                        self.security_pid = self.ultimate['confd'].show_platform(hw_cedge, False)
                    if (
                        ('ASR' in self.security_pid)
                        or ('C8500-12X' in self.security_pid)
                        or ('C8500-20X6C' in self.security_pid)
                    ):
                        return True
                    if feature == 'ssl':
                        if ('C11' in self.security_pid) or ('ISR11' in self.security_pid) or \
                            ('ISR42' in self.security_pid) or ('C8200-UCPE-1N8' in self.security_pid) or \
                                ('C8500L-8S4X' in self.security_pid):
                            return True
            return False
        except Exception as ex:
            self.logger.error("Exception in check_utd_ssl_support: %s" % ex)
            return False

    def check_instrumented_cedge_image(self, machine):
        '''
        Function used to check if a cEDGE image is CTC++ instrumented image or not
        Returns True or False based on result
        '''
        self.logger.debug("Starting the process to check if image is intrumented or not in %s" % machine)
        res = self.ultimate['iosxe'].exec_cmd_in_binos_and_return_output(machine, 'ls /usr/bin/cflow')
        expected_output = '/usr/bin/cflow '
        if len(res) == len(expected_output):
            return True
        else:
            return False

    def dat_file_based_on_buildid(self, dst):
        '''Filters dat files of intrumented images based on build id
        segregates and creates a dictionary of dat files with keys as their build id's
        '''
        local = dict()
        arr = os.listdir(dst)
        for datfile in arr:
            tarf = tarfile.open(dst + datfile)
            x = tarf.getnames()[-1]
            index = x.rfind('_')
            build_id = x[index + 1 : x.find('.dat')]
            url = 'https://cerebro.cisco.com/getCTCBuildDetails?build_id={}&userid=rajatya'.format(build_id)
            headers = {'Content-Type': 'application/json'}
            response = requests.request("GET", url, headers=headers)
            res = response.json()
            if res['build_details']:
                d = res['build_details'].pop()
                if d['build_id'] not in local:
                    local[d['build_id']] = d
                    local[d['build_id']]['path'] = []

                if d['build_id'] in local:
                    local[d['build_id']]['path'].append(datfile)

        return local


    def upload_to_cerebro(self):

        '''
        This code checks for Cflow image for every Cedge in tb.
        Runs clfow dump , collect dat files for every Cedge in tb.
        Creates a cerebro payload for doing a POST request to Cerebro API
        The cerebro report is submitted automatically.
        '''

        # creating directories as per regress db id's
        self.logger.info("Starting the process to collect coverage data for Cerebro from cedges VMs")
        cflow_file_path = expanduser("~") + "/Cflow_files_vtest"
        if not os.path.exists(cflow_file_path):
            os.makedirs(cflow_file_path)
        db_cflow_path = expanduser("~") + "/Cflow_files_vtest/{}".format(self.db_build_id)
        if not os.path.exists(db_cflow_path):
            os.makedirs(db_cflow_path)
        dat_cedge_version_map = dict()
        # Check if instrumented image exists and assigne dat file location based on platform type

        for machine in self.tb.machines():
            if self.tb.is_cedge(machine):
                cedge_version = self.tb.get_cedge_version(machine)[1][:5]
                cedge_platform = self.tb.get_platform_type_cedge(machine, self.ultimate['confd'])[1]
                # If not instrumented bail out and go to next machine
                if not self.check_instrumented_cedge_image(machine):
                    self.logger.info(" No Instrumented image found in %s , moving to next machine" % machine)
                    continue

                self.logger.info("Instrumented image found in %s" % machine)
                # Assign storage of dat files from platform type of device

                if 'ASR-1006-X' in cedge_platform:
                    storage = 'harddisk'
                else:
                    storage = 'bootflash'

                dst = db_cflow_path + '/'
                vm_dst = os.path.join(self.logs_sub_dir, machine, 'var_logs_%s' % machine)
                self.tb.mkpath(vm_dst)
                time_out_dump = 600
                try:

                    self.logger.info("Executing a coverage data dump on %s" % machine)
                    self.ultimate['iosxe'].exec_cmd_in_binos(machine, '/usr/bin/cflow dump', time_out_dump)
                except Exception as e:
                    self.logger.info("Failed to complete dat file dump , %s" % e)
                dat_file_name = machine + '_' + 'dat_file'
                if machine not in dat_cedge_version_map:
                    dat_cedge_version_map[machine] = cedge_version
                self.ultimate['iosxe'].delete_force_recursive(machine, 'bootflash:{}.tar.gz'.format(dat_file_name))
                try:

                    self.ultimate['iosxe'].exec_cmd_in_binos(
                        machine,
                        'tar -czf /bootflash/{}.tar.gz /{}/cflow/*.dat'.format(dat_file_name, storage),
                        timeout=180,
                    )
                    self.logger.info('Copying dat files for {}:{}.tar.gz to: {}'.format(machine, dat_file_name, dst))
                    self.tb.copy_from_machine(machine, '{}.tar.gz'.format(dat_file_name), dst)
                    file_name = dst + '{}.tar.gz'.format(dat_file_name)
                    subprocess.call('tar -xvzf %s -C %s --warning=no-timestamp' % (file_name, vm_dst), shell=True)
                    src = Path(vm_dst) / 'bootflash/cflow'
                    ucs_dst = (
                        Path(vm_dst) / 'bootflash/vtestdebug/cflow'
                    )  # following the same dir convention as admintech and collect cflow
                    if src.exists():
                        ucs_dst.parent.mkdir(parents=True, exist_ok=True)
                        # Move the directory
                        shutil.move(str(src), str(ucs_dst))
                        self.logger.info("Moved {} to {}".format(src, ucs_dst))
                    else:
                        self.logger.info("Source directory {} does not exist.".format(src))
                except Exception as e:
                    self.logger.info("Failed to copy dat file from machine  , %s" % e)
        local = self.dat_file_based_on_buildid(dst)
        cerebro_payload = dict(
            [
                ("args_st", self.args_string),
                ("suite_name", self.suite_name),
                ("exec_date", self.db_exec_date),
                ("tb_name", self.db_tb_name),
                ("reg_id", self.db_build_id),
                ("userid", self.coverage_meta_data),
            ]
        )
        # Create a Cerebro report object for each build id
        build_id_ojects = {}

        for build_id in list(local.keys()):
            build_id_ojects[build_id] = UploadTest(cerebro_payload, build_id, local, dst, dat_cedge_version_map)
            res = build_id_ojects[build_id].post_request()
            if res:
                self.logger.info("Successfully uploaded the suite coverage data to Cerebro")
            else:
                self.logger.info("Failed to upload report to Cerebro")
        subprocess.call('rm -rf %s' % dst, shell=True)

    def selinux_denial_check(self):
        '''
        This function checks for selinux denial checks on the cEdge devices
        '''
        try:
            local_path = '%s/selinux' % (self.logs_sub_dir)
            cmd = 'mkdir %s' % local_path
            os.system(cmd)
            self.tb.sudo(['sudo', 'chmod', '-R', '777', '%s' % local_path], shell=True)
            for machine in self.tb.machines():
                if self.tb.is_cedge(machine) and float(self.ultimate['confd'].get_version(machine)) >= 17.08:
                    file_name = '%s-show_audit.log' % (machine)
                    machine_config = self.tb.config['machines'][machine]
                    hostname = machine_config.get('hostname', machine)
                    denial_count = self.ultimate['confd'].selinux_denial_check(machine)
                    if len(denial_count[0]) == 0:
                        self.logger.info("Couldn't parse denial count for Machine %s:" %(hostname))
                    elif denial_count[0] == "0":
                        self.logger.info("##############################################################################")
                        self.logger.info("No SELinux Denial logs seen for Machine %s :: %s" %(hostname, denial_count[1]))
                        self.logger.info("##############################################################################")
                    else:
                        self.logger.info(
                            "##############################################################################"
                        )
                        self.logger.info("SElinux Denial logs seen for Machine %s :: %s" % (hostname, denial_count[1]))
                        self.logger.info(
                            "##############################################################################"
                        )
                        cmd = 'show platform software audit all | redirect bootflash:%s' % (file_name)
                        self.ultimate['confd'].show_cli_cmd(machine, cmd)
                        # copy audit log to selinux folder under vtest logs
                        self.tb.copy_from_machine(machine, file_name, local_path)
                        # cleanup the audit log on device bootflash
                        self.ultimate['iosxe'].delete_force_recursive(machine, 'bootflash:%s' % file_name)
            # check if the auto mount path is accessible and copy the audit logs folder to auto path
            auto_path = '/auto/selinux_vtest/SELinux_vtest_logs'
            if not os.path.exists(auto_path):
                self.logger.info('auto path is not accessible on this tesbted')
            else:
                dest = '/auto/selinux_vtest/SELinux_vtest_logs/%s/' % (self.db_build_id)
                cmd = 'mkdir %s' % (dest)
                os.system(cmd)
                cmd1 = 'cp -rp %s/ %s' % (local_path, dest)
                os.system(cmd1)
                self.logger.info('copied audit logs to auto mount path %s' % dest)
        except Exception as e:
            self.logger.error('SElinux Denial checks not done, %s' % e)
            return
        # File CDETS for the SElinux Denials
        # Get the ABS archive path for the image label of cEdge version
        try:
            image_label = self.label
            selinux_user = os.environ.get('user_name', platform_mapping.CONFIG_DICT.get('user_name'))
            selinux_server = platform_mapping.CONFIG_DICT.get('server_name')
            template_file = str(Paths().addons('selinux/template.input'))
            cedge_platform = ''
            dest = "{}/selinux".format(dest)
            for machine in self.tb.machines():
                if self.tb.is_cedge(machine) and float(self.ultimate['confd'].get_version(machine)) >= 17.08:
                    if not image_label:
                        result = self.ultimate['confd'].get_cedge_image_label(machine)
                        if result[0]:
                            image_label = result[1]
                            self.logger.info('Image Label : %s' % image_label)
                    cedge_platform = self.ultimate['confd'].show_platform(machine)
                    # Fetch platform mapping
                    for key, val in platform_mapping.PLATFORM_DICT.items():
                        if key in cedge_platform:
                            platform_name = val
                            self.logger.info('Mapping : %s' % platform_name)
                            break
                    else:
                        raise Exception('Platform mapping not found in dictionary')

                    # Execute ABS Cli
                    if self.label:
                        self.logger.info('Label:: %s' % self.label)
                        image_label = self.label
                    cmd = '/auto/binos-tools/bin/mcpre_abs details -l %s -n' % image_label
                    sshProcess = subprocess.Popen(
                        [
                            "/usr/bin/ssh",
                            "-T",
                            "-o",
                            "StrictHostKeyChecking=no",
                            "{user}@{server}".format(user=selinux_user, server=selinux_server),
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        universal_newlines=True,
                        bufsize=0,
                    )
                    sshProcess.stdin.write(cmd)
                    sshProcess.stdin.close()
                    return_code = sshProcess.wait()
                    if return_code != 0:
                        raise Exception('Could not retrieve ABS archive path')
                    output = (
                        sshProcess.stdout.read().decode('utf-8')
                        if sys.version_info <= (3, 2)
                        else sshProcess.stdout.read()
                    )
                    archive_path = re.search(r'.*(Archive Location:.*)', output, re.M)
                    binos_root = archive_path.group(1).split(':')[1].strip()
                    if platform_name == 'goldbeach':
                        platform_obj_path = (
                            '_gen_comp_obj-{device_type}_universalk9_ias-x86_64_cge7-{platform_suffix}'.format(
                                device_type=platform_name, platform_suffix=platform_name
                            )
                        )
                    else:
                        platform_obj_path = (
                            '_gen_comp_obj-{device_type}_universalk9-x86_64_cge7-{platform_suffix}'.format(
                                device_type=platform_name, platform_suffix=platform_name
                            )
                        )
                    # Executed audit2cdet commands
                    sshProcess = subprocess.Popen(
                        [
                            "/usr/bin/ssh",
                            "-T",
                            "-o",
                            "StrictHostKeyChecking=no",
                            '{user}@{server}'.format(user=selinux_user, server=selinux_server),
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                        bufsize=0,
                    )
                    source_file = os.path.join(binos_root, 'binos', 'contrib', 'refpolicy', 'scripts', 'functions.sh')
                    sshProcess.stdin.write('echo ' + binos_root + '\n')
                    sshProcess.stdin.write('cd ' + binos_root + '/binos/contrib/refpolicy/' + platform_obj_path + '\n')
                    sshProcess.stdin.write('uname -a \n')
                    sshProcess.stdin.write('pwd \n')

                    subprocess.call("cp {} {}/".format(str(template_file), dest), shell=True)
                    template_file = os.path.join(dest, 'template.input')

                    cmd1 = "audit2cdets -a {}/{} -i".format(dest, file_name)
                    cmd2 = "audit2cdets -a {}/{} -S -d {}/{}'_cdets'".format(dest, file_name, dest, machine)
                    cmd3 = "audit2cdets -a {}/{} -S -d {}/{}'_cdets' -F -T {}".format(
                        dest, file_name, dest, machine, template_file
                    )
                    sshProcess.stdin.write('bash -c ". {}; {}; {}" \n'.format(source_file, cmd1, cmd2))

                    # Generate Reg_Eval.txt file enclosure
                    enclosure = reg_eval.reg_eval(self, machine, dest, template_file)
                    if enclosure:
                        self.logger.info('Reg_Eval.txt file generated')
                    else:
                        self.logger.error('Reg_Eval.txt couldnt be generated')

                    # copy Reg_Eval.txt file to all enclosures folders
                    reg_eval_txt = os.path.join(dest, 'Reg_Eval.txt')
                    copy_cmd = "echo {}/{}_cdets/bug*/enclosures* | xargs -n 1 cp {}".format(
                        dest, machine, str(reg_eval_txt)
                    )
                    sshProcess.stdin.write('bash -c ". {}; {}; {}" \n'.format(source_file, copy_cmd, cmd3))

                    sshProcess.stdin.close()
                    exit_code = sshProcess.wait(timeout=900)
                    # Fetch output
                    for line in sshProcess.stdout:
                        self.logger.info(line.strip())
                    if exit_code != 0:
                        for err in sshProcess.stderr:
                            self.logger.error(err.strip())
                        raise Exception('Error in audit2cdets command')
        except subprocess.TimeoutExpired:
            self.logger.error('Timeout Expired in audit2cdets')
            sshProcess.kill()
        except Exception as e:
            self.logger.error('SElinux CEDTS filing failed, %s' % e)
            return

    def session_wrappers(self):
        # type: () -> typing.Iterator[AbstractSession]
        try:
            self.ultimate
        except AttributeError:
            return
        else:
            for session in list(self.ultimate.values()):
                if not isinstance(session, AbstractSession):
                    continue
                yield session

    def override_tc_result_based_on_func_tags(self, tc_result, retval, func, tags):
        # type: (str, int, str, typing.Set[str]) -> typing.Tuple[str, int]
        if tc_result == TCResult.NOT_RUN:
            return (tc_result, retval)

        expected_tc_results = {
            'should_abort': TCResult.ABORTED,
            'should_error': TCResult.ERRORED,
            'should_pass': TCResult.PASS,
            'should_fail': TCResult.FAIL,
            'should_skip': TCResult.SKIPPED,
            'should_block': TCResult.BLOCKED,
        }
        for tag in tags:
            if tag in expected_tc_results:
                if tc_result == expected_tc_results[tag]:
                    new_tc_result = TCResult.PASS
                    new_retval = RETVAL_SUCCESS
                else:
                    new_tc_result = TCResult.FAIL
                    new_retval = RETVAL_FAILURE
                self.logger.info(
                    f"Override TCResult of {func.name} from {tc_result!r} to {new_tc_result!r} due to tag {tag!r}"
                )
                return (new_tc_result, new_retval)
        # If no tags matched, keep result intact
        return (tc_result, retval)

    @staticmethod
    def subtest_casting_is_needed(subtests):
        # type: (typing.Any) -> bool
        return isinstance(subtests, list) and subtests and not isinstance(subtests[0], (list, tuple, int, str))

    def enable_disable_dhcp_server(self, enable, dhcp_server_intf):
        """
        Enables / disables DHCP server used for allocating MGMT IP address for HW devices
        Parameters:
            enable (bool):
                True: Starts DHCP server
                False: Stops DHCP server
            dhcp_server_intf (str):
                DHCP server interface.
                If enable is True, static IP address "10.0.99.1/24"
                is assigned to this interface before starting DHCP server.
                If enable is False, staitc IP address "10.0.99.1/24"
                is removed from this interface after stopping DHCP server.
        """
        if enable:
            self.logger.info(
                "Configuring DHCP server static IP address '10.0.99.1/24' to interface '{0}'".format(dhcp_server_intf)
            )
            result = subprocess.call(["sudo", "ip", "addr", "add", "10.0.99.1/24", "dev", dhcp_server_intf])
            if result == 0:
                self.logger.info(
                    "Successfully configured interface '{0}' with static IP '10.0.99.1/24'".format(dhcp_server_intf)
                )
            else:
                self.logger.error(
                    "Failed to configure interface '{0}' with static IP '10.0.99.1/24'".format(dhcp_server_intf)
                )

            self.logger.info("Starting DHCP server...")
            result = subprocess.call(["sudo", "service", "isc-dhcp-server", "start"])
            if result == 0:
                self.logger.info("Start DHCP server successful")
            else:
                self.logger.error("Start DHCP server failed")
        else:
            self.logger.info("Stopping DHCP server...")
            result = subprocess.call(["sudo", "service", "isc-dhcp-server", "stop"])

            if result == 0:
                self.logger.info("Stop DHCP server successful")
            else:
                self.logger.error("Stop DHCP server failed")

            self.logger.info(
                "Unconfiguring DHCP server static IP address '10.0.99.1/24' from interface '{0}'".format(
                    dhcp_server_intf
                )
            )
            result = subprocess.call(["sudo", "ip", "addr", "del", "10.0.99.1/24", "dev", dhcp_server_intf])
            if result == 0:
                self.logger.info(
                    "Successfully unconfigured interface '{0}' with static IP '10.0.99.1/24'".format(dhcp_server_intf)
                )
            else:
                self.logger.error(
                    "Failed to unconfigure interface '{0}' with static IP '10.0.99.1/24'".format(dhcp_server_intf)
                )

    def log_args_with_help(self, parser):
        """
        Go over command line arguments and
        log them in the more descriptive way in log file.

        I.e. cryptic -ntr -ntg -ns, will be presented as:

         2024-11-28 11:16:45,539 - DEBUG - Help for provided arguments:

        Used -ntr option: -ntr, --no_transport_routing
            Bring up OMP suite without OSPF transport routing

        Used -ns option: -ns, --nosanity
            No help available

        Used -ntg option: -ntg, --no_traffic_generation
            Do not run tests with Spirent traffic generator
        """
        argv = sys.argv[1:]
        founds = set()
        message = ["Help for provided arguments:\n\n"]
        for arg in argv:
            for action in parser._actions:
                if action.option_strings and arg in action.option_strings and arg not in founds:
                    help = "No help available" if action.help == argparse.SUPPRESS else action.help
                    msg = "Used {} option: {}\n\t{}\n\n".format(arg, ', '.join(action.option_strings), help)
                    message.append(msg)
                    founds.add(arg)
                    break
        self.logger.debug("".join(message))

    @property
    def machines_with_sessions(self):
        if hasattr(self, "_machines_with_sessions"):
            return self._machines_with_sessions

        machines = set()
        for session in self.sessions.values():
            if isinstance(session, dict):
                machines.update(str(m).lower() for m in session.keys())

        self._machines_with_sessions = machines
        return machines

class VersionCheckThread(Thread):
    def __init__(self, machine, runner):
        self.machine = machine
        self.runner = runner
        self.tb = runner.tb
        self.confd = runner.confd
        self.versions = set()
        self.platform = "N/A"
        self.non_vmanage_versions = set()
        self.vmanage_versions = set()
        self.message = ''
        self.has_error = False
        self.t_start = None
        self.t_end = None
        self.image_version = None
        self.modems_pids = ""
        super(VersionCheckThread, self).__init__()

    def run(self):
        try:
            machine = self.machine
            machine_personality = self.tb.personality(machine)
            if self.tb.is_nfvis(machine):
                return
            ver = self.confd.show_version(machine, False)
            ver1 = self.confd.show_buildinfo(machine, False)
            self.platform = self.confd.show_platform(machine, False)
            modems = self.confd.get_cedge_inventory_modems(machine)
            self.modems_pids = ",".join(m["pid"] for m in modems)
            if ver[0] is False:
                self.has_error = True
                self.message = '%s: Could not get the version' % machine
                return
            else:
                self.image_version = ver[1]
                self.message = '%s: %s %s' % (machine, ver[1], ver1[1])
                branch, build_no = misc.parse_version(ver[1])
                self.versions.add((branch, build_no))
                if machine_personality != 'vmanage':
                    self.non_vmanage_versions.add((branch, build_no))
                else:
                    self.vmanage_versions.add((branch, build_no))
                # to inform user that not supported version is being run o vedge:
                if machine_personality in ['vedge', 'linux_vedge', 'ztp']:
                    if LooseVersion(ver[1]) >= LooseVersion("20.10"):
                        self.has_error = True
                        self.message += " vedge:%s is running >=20.10" % machine_personality
        except Exception as e:
            self.has_error = True
            self.message += " Exception when checking version on %s:\n%s" % (machine, str(e))

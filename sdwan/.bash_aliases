alias ll="ls -ltrFa"

alias a27="source /opt/venv/vtest2.7/bin/activate"
alias a36="source /opt/venv/vtest3.6/bin/activate"
alias a38="source /home/tester/venv/vtest/bin/activate"
alias ap3="source ~/.p3/bin/activate"
alias dac="deactivate"
alias sshpm5="ssh-keygen -R 10.0.99.15 -f ~/.ssh/known_hosts 2>/dev/null; sshpass -p 'ci5co#Net' ssh -o StrictHostKeyChecking=accept-new admin@10.0.99.15"
alias sshpm1="ssh-keygen -R 10.0.99.11 -f ~/.ssh/known_hosts 2>/dev/null; sshpass -p 'ci5co#Net' ssh -o StrictHostKeyChecking=accept-new admin@10.0.99.11"
alias sshvm12="sshpass -p 'ci5co#Net' ssh -o ControlMaster=no -o ControlPath=none -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null -l admin 10.0.1.32"
alias sshvm="sshpass -p 'ci5co#Net' ssh -o ControlMaster=no -o ControlPath=none -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null -l admin "

alias capturelog="tmux capture-pane -pS -100000 > /home/tester/yaml/logs/tmux-pane.log"

alias cdv="cd /home/tester/vtest"
alias cdkt="cd /home/tester/kaidyan/test"
alias cdks="cd /home/tester/kaidyan/scripts"

alias cdtb="cd /home/tester/testbeds/tb"

alias cdy="cd /home/tester/yaml"
alias cdi="cd /home/tester/images"

alias cdl="cd /home/tester/vtest/tests/logs/"
alias cds="cd /home/tester/vtest/tests/scripts"

alias checkrun="ps -ef | grep vtest | grep -P 'testbed|run'"
alias clearrun="checkrun | awk '{print $2}' | xargs -r kill -9"

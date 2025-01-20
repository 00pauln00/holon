from ansible.plugins.lookup import LookupBase
from genericcmd import *

def check_for_ports(conf_params, genericcmdobj):
    port = int(conf_params['srv_port'])
    client_port = int(conf_params['client_port'])

    for p in (port, client_port):
        genericcmdobj.port_check(p)

def install_python_modules(genericcmdobj):
    genericcmdobj.install_python_modules()

class LookupModule(LookupBase):
    def run(self, terms, **kwargs):

        config_params_dict = terms[0]
        startup_check = config_params_dict['startup_check']
        
        #Create object for genericcmd
        genericcmdobj = GenericCmds()
        if startup_check == "port_check":
            port_check = check_for_ports(config_params_dict, genericcmdobj)
            return []
        else:
            install_modules = install_python_modules(genericcmdobj)
            return []


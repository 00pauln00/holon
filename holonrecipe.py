import json, os, subprocess, collections, logging
import time as time_global
from datetime import datetime
from raftconfig import RaftConfig
from raftserver import RaftServer
from raftclient import RaftClient
from raftprocess import RaftProcess
from inotifypath import InotifyPath
from niovacluster import NiovaCluster
from ctlrequest import * 
from genericcmd import GenericCmds

class HolonRecipeBase:

    logger = {}
    name = ''
    desc = ''
    parent = ''

    '''
        Method: dry_run
        Purpose: exec dry run conditions
        Parameters:
    '''
    def dry_run(self, params):
        self.logger.log(logging.DEBUG, "dry_run!")
        raise NotImplementedError

    '''
        Method: pre_run
        Purpose: exec pre run conditions
        Parameters:
    '''
    def pre_run(self, params):
        self.logger.log(logging.DEBUG, "pre_run!")
        raise NotImplementedError

    '''
        Method: run
        Purpose: exec run conditions
        Parameters:
    '''
    def run(self, params):
        self.logger.log(logging.DEBUG, "run!")
        raise NotImplementedError

    '''
        Method: post_run
        Purpose: exec post run conditions
        Parameters:
    '''
    def post_run(self, params):
        self.logger.log(logging.DEBUG, "post_run!")
        raise NotImplementedError

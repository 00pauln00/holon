#!/usr/bin/python3
# PYTHON_ARGCOMPLETE_OK

import os, sys, importlib, time, logging, fnmatch, errno, argparse, argcomplete
from raftconfig import RaftConfig
from inotifypath import InotifyPath
from niovacluster import NiovaCluster
from genericcmd import GenericCmds
from shutil import rmtree
from os.path import abspath
from alive_progress import alive_bar

#Create object for GenericCmds Class
genericcmdobj = GenericCmds()

# Generate RAFT UUID
raft_uuid = genericcmdobj.generate_uuid()

'''
Default values for the command line parameters
'''
dir_path = "/tmp/holon_recipes_run"
log_file_path = "/var/tmp/holon_%s.log" % (raft_uuid)
npeers = 5
port = 6000
client_port = 13000
dry_run = False
disable_post_run = False
recipe_name = ""
print_desc = False
print_ancestry = False
skip_post_run = False

'''
It list the recipe names from /recipes directory and
split it from ".py" and then store it into rec_name[]
rec_name: List of recipe name.
'''
listOfFiles = os.listdir('./recipes')
pattern = "*.py"
rec_name = []
valid_recipe = 0
for files in listOfFiles:
    if fnmatch.fnmatch(files, pattern):
        x = files.split(".py")
        rec_name.append(x[0])
        if x[0] == recipe_name:
            valid_recipe = 1
            break

parser = argparse.ArgumentParser()

parser.add_argument('recipe', type = str, help = "recipe_name", choices = rec_name)

'''
This method used for Tab completion.
It interactively printing the recipes
'''
argcomplete.autocomplete(parser)

parser.add_argument('-P', action = "store", dest = "dir_path", help = "directory path to create config/ctl/raftdb files")
parser.add_argument('-p', action = "store", dest = "port", help = "server port")
parser.add_argument('-c', action = "store", dest = "client_port", help = "client port")
parser.add_argument('-o', action = "store", dest = "npeers", help = "number of peers in the cluster")

parser.add_argument('-l', action = "store", dest = "log_file_path", help = "log file path")

parser.add_argument('-d', action = "store_true", dest = "dry_run", default = False, help = "dry run to print ancestry and create config files")
parser.add_argument('-D', action = "store_true", dest = "disable_post_run", default = False, help = "disable post run on failure")
parser.add_argument('-print-desc', action = "store_true", dest = "print_desc", default = False, help = "print description")
parser.add_argument('-print-ancestry', action = "store_true", dest = "print_ancestry", default = False, help = "print ancestry")
parser.add_argument('-R', action = "store_true", dest = "skip_post_run", default = False, help = "Disable post run")

args = parser.parse_args()

if args.dir_path == None:
    dir_path = dir_path
    genericcmdobj.make_dir(dir_path)
else:
    dir_path = abspath(args.dir_path)
    genericcmdobj.make_dir(dir_path)

if args.port == None:
    port = int(port)
else:
    port = int(args.port)

if args.client_port == None :
    client_port = int(client_port)
else:
    client_port = int(args.client_port)

if args.npeers == None:
    npeers = int(npeers)
else:
    npeers = int(args.npeers)

if args.log_file_path == None:
    log_file_path = log_file_path
else:
    log_file_path = abspath(args.log_file_path)

dry_run = args.dry_run
disable_post_run = args.disable_post_run
print_desc = args.print_desc
print_ancestry = args.print_ancestry
skip_post_run = args.skip_post_run
recipe_name = args.recipe

if port >= 65536:
    print(f"Port (%d) should be less than 65536" % port)
    exit()

if client_port >= 65536:
    print(f"Client Port (%d) should be less than 65536" % client_port)
    exit()

logging.basicConfig(filename=log_file_path, level=logging.DEBUG, format='%(asctime)s [%(filename)s:%(lineno)d] %(message)s')

logging.warning("Holon Directory path: %s" % dir_path)
logging.warning("Log file path %s" % log_file_path)
logging.warning("Number of Servers: %s" % npeers)
logging.warning("Port no:%s" % port)
logging.warning("Client Port no:%s" % client_port)
logging.warning("Recipe: %s" % recipe_name)

'''
Iterate over the recipe hierarchy and gather the recipe objects.
'''

recipe_arr = []
recipe = ".%s" % recipe_name
RecipeModule = importlib.import_module(recipe, package="recipes")
logging.warning(RecipeModule)

RecipeClass = RecipeModule.Recipe

recipe_arr.append(RecipeClass)
parent = RecipeClass().pre_run()

'''
Call pre_run method of all recipes in the hierarchy to build the recipe
tree for execution.
'''
while parent != "":
    parent = ".%s" %  parent
    parentRecipeModule = importlib.import_module(parent, package="recipes")

    RecipeClass = parentRecipeModule.Recipe
    recipe_arr.append(RecipeClass)
    parent = RecipeClass().pre_run()

logging.warning("Recipe Hierarchy from Root => Leaf")
for r in reversed(recipe_arr):
    logging.warning("%s" % r().name)

'''
Print the recipe description
'''
if print_desc == True:
    recipe = ".%s" % recipe_name
    RecipeModule = importlib.import_module(recipe, package="recipes")
    logging.warning(RecipeModule)

    RecipeClass = RecipeModule.Recipe
    RecipeClass().print_desc()
    print("Parent: %s" % RecipeClass().parent)
    exit()

if dry_run == False:
    #It prints the base_dir path
    dir_path = "%s/%s" % (dir_path, raft_uuid)
    logging.warning("The test root directory is: %s" % dir_path)

    raftconfobj = RaftConfig(dir_path, raft_uuid, genericcmdobj)

    raftconfobj.generate_raft_conf(genericcmdobj, npeers, "127.0.0.1", port,
                                client_port)

'''
print ancestors will only print the ancestors for the recipe and will exit
or
perform dry run : dry_run also prints ancestry but it also creates config files.
'''
if print_ancestry == True or dry_run == True :
    print("Ancestors: ", end="")
    for r in (recipe_arr):
        if r().name != recipe_name:
            if r().parent == "":
                print(f"%s" % r().name)
            else:
                print(f"%s, " % r().name, end="")
    if len(recipe_arr) == 1 :
        print("none ")
    exit()

# Create Cluster object
clusterobj = NiovaCluster(npeers)

# Make sure server port and client port are not in use
for p in (port, client_port):
    genericcmdobj.port_check(p)


#If user doesn't have to specify -P then it will run with default values
if os.path.exists(dir_path):
    logging.warning("Base directory path : %s" % dir_path)

logging.warning(f"Raft conf and server configs generated")

inotifyobj = InotifyPath(dir_path, True)

clusterobj.raft_conf_obj_store(raftconfobj)

clusterobj.inotify_obj_store(inotifyobj)

#Storing log file path in clusterobj
clusterobj.log_path_store(log_file_path)

#It prints the log_file path
print("Log file path : %s" % log_file_path)
logging.warning("The log file path is: %s" % log_file_path)

'''
Executing recipes from Root to Leaf order.
'''
with alive_bar(len(recipe_arr)) as bar:
    for r in reversed(recipe_arr):
        logging.warning("Running Recipe %s" % r().name)
        recipe_failed = r().run(clusterobj)
        bar()
        if recipe_failed == 1:
            logging.error("%s recipe Failed" % r().name)
            print("Error: Terminating recipe hierarchy execution")
            logging.error("Error: Terminating recipe hierarchy execution")
            print("%s ========================== Failed" % r().name)
            break
        else:
            print("%s ========================== OK" % r().name)
            logging.warning("%s ========================== OK" % r().name)
'''
Even after holon terminates, skip the post_run
method so that processes will keep running.
'''
if skip_post_run == True:
    print("Processes will keep running even after holon terminates")
    exit(1)
'''
If any recipe failed and disable_post_run is set, skip the post_run
method so that processes do not get terminated and can be used for
debugging.
'''
if recipe_failed and disable_post_run:
    exit(1)

'''
Calling post_run method in the reverse order i.e Leaf to Root for
cleaning up the files/processes which that specific recipe had created/started.
'''

for r in recipe_arr:
    logging.warning("Post Run Recipe: %s" % r().name)
    r().post_run(clusterobj)

#It will remove all config files
raftconfobj.delete_config_file()

#It will remove all files and directory
rmtree(dir_path)


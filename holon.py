#!/usr/bin/python3

import os, sys, importlib, getopt, logging, fnmatch, errno
from raftconfig import RaftConfig
from inotifypath import InotifyPath
from niovacluster import NiovaCluster
from genericcmd import GenericCmds
from shutil import rmtree


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

def Usage():
    print("usage: holon.py [OPTIONS] <Recipe Name>",
          "To run the recipe:\n",
          "mandatory arguments:",
          "-P             <Directory Path>\n",
          "positional arguments:",
          "<Recipe Name> (Note: Recipe name should be last parameter)\n",
          "optional arguments:" ,
          "-p             <Port No>" ,
          "-c             <Client Port>" ,
          "-o             <Number of servers to run>",
          "-l             <Log file path>" ,
          "-d             <Dry Run Recipes>" ,
          "--print-desc   <print the recipe's description>\n"
          "-D             <Disable post run on error>",
          "-h, --help     <show this help message and exit>", sep ="\n")
try:
    options, args = getopt.getopt(
            sys.argv[1:], "P:o:p:c:l:print-disc:dhD",["dir_path=",
                        "npeers=",
                        "port=", "client_port=",
                        "log_path=", "print-desc",
                        "dry-run", "disable-post-run", "help"])
except getopt.GetoptError:
    Usage()
    sys.exit(1)

#Running holon with no arguments should print the help message
if len(sys.argv) == 1:
   Usage()
   exit()

for name, value in options:
    if name in ('-P', '--dir_path'):
        dir_path = value
        genericcmdobj.make_dir(dir_path)
    if name in ('-l', '--log_path'):
        log_file_path = value
        if not os.path.exists(os.path.dirname(log_file_path)):
            try:
                os.makedirs(os.path.dirname(log_file_path))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
    if name in ('-o', '--npeers'):
        npeers = int(value)
    if name in ('-p', '--port'):
        port = int(value)
    if name in ('-c', '--client_port'):
        client_port = int(value)
    if name in ('-d', "--dry-run"):
        dry_run = True
    if name in ('-print-desc', "--print-desc"):
        print_desc = True
    if name in ('-D', "--disable-post-run"):
        disable_post_run = True
    if name in ('-h', "--help"):
        Usage()
        sys.exit(0)

if port >= 65536:
    print(f"Port (%d) should be less than 65536" % port)
    exit()

if client_port >= 65536:
    print(f"Client Port (%d) should be less than 65536" % client_port)
    exit()

recipe_name = sys.argv[len(sys.argv) -1]

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

if valid_recipe == 0:
    print("Error: Invalid recipe name passed")
    print("Select from valid recipes:")
    for r in rec_name:
        print(r)
    exit()

logging.basicConfig(filename=log_file_path, level=logging.DEBUG, format='%(asctime)s %(message)s')

logging.warning("Holon Directory path: %s" % dir_path)
logging.warning("Log file path %s" % log_file_path)
logging.warning("Number of Servers: %s" % npeers)
logging.warning("Port no:%s" % port)
logging.warning("Client Port no:%s" % client_port)
logging.warning("Recipe: %s" % recipe_name)

# Print the recipe description
if print_desc:
    recipe = ".%s" % recipe_name
    RecipeModule = importlib.import_module(recipe, package="recipes")
    logging.warning(RecipeModule)

    RecipeClass = RecipeModule.Recipe
    RecipeClass().print_desc()
    print("Parent: %s" % RecipeClass().parent)
    exit()

recipe_arr = []

'''
Iterate over the recipe hierarchy and gather the recipe objects.
'''

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
dry_run will only print the ancestors recipe names for the given recipe.
'''
if dry_run:
    print("Ancestors: ", end="")
    for r in (recipe_arr):
        if r().name != recipe_name:
            if r().parent == "":
                print(f"%s" % r().name)
            else:
                print(f"%s, " % r().name, end="")
    exit()

# Make sure server port and client port are not in use
for p in (port, client_port):
    genericcmdobj.port_check(p)

# Create Cluster object
clusterobj = NiovaCluster(npeers)

#It prints the base_dir path
dir_path = "%s/%s" % (dir_path, raft_uuid)
logging.warning("The test root directory is: %s" % dir_path)

raftconfobj = RaftConfig(dir_path, raft_uuid, genericcmdobj)

raftconfobj.generate_raft_conf(genericcmdobj, npeers, "127.0.0.1", port,
                                client_port)

'''
dry_run will create config files and  print the ancestors recipe names for the given recipe.
'''
if dry_run:
    print("Ancestors: ", end="")
    for r in (recipe_arr):
        if r().name != recipe_name:
            if r().parent == "":
                print(f"%s" % r().name)
            else:
                print(f"%s, " % r().name, end="")

    exit()

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
for r in reversed(recipe_arr):
    logging.warning("Running Recipe %s" % r().name)
    recipe_failed = r().run(clusterobj)
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

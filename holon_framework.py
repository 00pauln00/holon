import os, sys, importlib, getopt, logging, fnmatch, socket, errno
from raftconfig import RaftConfig
from inotifypath import InotifyPath
from niovacluster import NiovaCluster
from genericcmd import GenericCmds

'''
Default values for the command line parameters
'''
dir_path = "/tmp/holon_recipes_run"
log_file_path = "/var/log/holon_recipe.log"
npeers = 5
port = 6000
client_port = 13000
dry_run = False
disable_post_run = False
recipe_name = ""

def Usage():
    print("-P <Directory path to store config, inotify files , etc>\n"
          "-l <Log file path>\n"
          "-o <Number of Servers>\n"
          "-p <Port>\n"
          "-c <Client Port>\n"
          "-r <Recipe Name>\n"
          "-d <Dry Run recipes>\n"
          "-D <Disable port run on error>\n"
          "-h Print Help")
try:
    options, args = getopt.getopt(
            sys.argv[1:], "P:o:p:c:r:l:dhD",["dir_path=",
                        "npeers=",
                        "port=", "client_port=", "recipe=",
                        "log_path=",
                        "dry-run", "disable-post-run", "help"])
except getopt.GetoptError:
    Usage()
    sys.exit(1) 

genericcmdobj = GenericCmds()

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
    if name in ('-r', '--recipe_name'):
        recipe_name = value
    if name in ('-d', "--dry-run"):
        dry_run = True
    if name in ('-D', "--disable-post-run"):
        disable_post_run = True
    if name in ('-h', "--help"):
        Usage()
        sys.exit(0)

if os.path.exists(dir_path) == False:
    print(f"Holon directory (%s) does not exist" % server_conf_path)
    exit()

if port >= 65536:
    print(f"Port (%d) should be less than 65536" % port)
    exit()

if client_port >= 65536:
    print(f"Client Port (%d) should be less than 65536" % client_port)
    exit()

# Make sure server port and client port are not in use
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for p in (port, client_port):
    try:
        s.bind(("127.0.0.1", p))
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            print(f"Port %d is already in use" % p)
            exit()

s.close()

if recipe_name == "":
    print("Recipe name is not provided......")
    print("Please select from the list of available recipes:")
    listOfFiles = os.listdir('./recipes')
    pattern = "*.py"
    for files in listOfFiles:
        if fnmatch.fnmatch(files, pattern):
            print ("- %s"% files)
    print(f"Please pass the recipe name as -r <recipe_name>")
    exit()

print(f"Holon Directory path: %s" % dir_path)
print(f"Log file path %s" % log_file_path)
print(f"Number of Servers: %s" % npeers)
print(f"Port no:%s" % port)
print(f"Client Port no:%s" % client_port)
print(f"Recipe: %s" % recipe_name)

logging.basicConfig(filename=log_file_path, level=logging.DEBUG, format='%(asctime)s %(message)s')

# Creare Cluster object
clusterobj = NiovaCluster(npeers)


# Generate RAFT UUID
raft_uuid = genericcmdobj.generate_uuid()

dir_path = "%s/%s" % (dir_path, raft_uuid)
print("The test root directory is: %s" % dir_path)
logging.warning("The test root directory is: %s" % dir_path)

raftconfobj = RaftConfig(dir_path, raft_uuid, genericcmdobj)

raftconfobj.generate_raft_conf(genericcmdobj, npeers, "127.0.0.1", port,
                                client_port)

logging.warning(f"Raft conf and server configs generated")

inotifyobj = InotifyPath(dir_path, True)

clusterobj.raft_conf_obj_store(raftconfobj)

clusterobj.inotify_obj_store(inotifyobj)

recipe_arr = []

'''
Iterate over the recipe hierarchy and gather the recipe objects.
'''

recipe = ".%s" % recipe_name
RecipeModule = importlib.import_module(recipe, package="recipes")
print(RecipeModule)

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
    logging.warn("%s" % r().name)

'''
dry_run will only print the ancestors recipe names for the given recipe.
'''
if dry_run:
    print("Ancestors:")
    for r in reversed(recipe_arr):
        if r().name != recipe_name:
            print(f"%s " % r().name)
    exit()

'''
Executing recipes from Root to Leaf order.
'''
for r in reversed(recipe_arr):
    logging.warning("Running Recipe %s" % r().name)
    recipe_failed = r().run(clusterobj)
    if recipe_failed == 1:
        print("Error: Terminating recipe hierarchy execution")
        logging.error("Error: Terminating recipe hierarchy execution")
        print("%s ========================== Failed" % r().name)
        break
    else:
        print("%s ========================== OK" % r().name)

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


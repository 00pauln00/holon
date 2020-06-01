import os, sys, importlib, getopt
from raftconfig import RaftConfig
from inotifypath import InotifyPath
from niovacluster import NiovaCluster
from genericcmd import GenericCmds

'''
Default values for the command line parameters
'''
server_conf_path = "/etc/holon/raftconf/"
inotify_path = "/tmp/inotify/"
init_path = "/tmp/init/"
npeers = 5
port = 6000
client_port = 13000
dry_run = False

def Usage():
    print("-s <server config path>\n"
          "-n <Inotify path>\n"
          "-i <Init command path>\n"
          "-o <Number of Servers>\n"
          "-p <Port>\n"
          "-c <Client Port>\n"
          "-r <Recipe Name>\n"
          "-d <Dry Run recipes>\n"
          "-h Print Help")
try:
    options, args = getopt.getopt(
            sys.argv[1:], "s:n:i:o:p:c:r:dh",["server_conf_path=",
                        "inotify_path=", "init_path=", "npeers=", 
                        "port=", "client_port=", "recipe=",
                        "dry-run", "help"])
except getopt.GetoptError:
    Usage()
    sys.exit(1) 

for name, value in options:
    if name in ('-s', '--server-conf'):
        server_conf_path = value
    if name in ('-n', '--inotify_path'):
        inotify_path = value
    if name in ('-i', '--init_path'):
        init_path = value
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
    if name in ('-h', "--help"):
        Usage()
        sys.exit(0)

if os.path.exists(server_conf_path) == False:
    print(f"Server config path (%s) does not exist" % server_conf_path)
    exit()

if os.path.exists(inotify_path) == False:
    print(f"Inotify path (%s) does not exist" % inotify_path)
    exit()

if os.path.exists(init_path) == False:
    print(f"Init path (%s) does not exist" % init_path)
    exit()

if port >= 65536:
    print(f"Port (%d) should be less than 65536" % port)
    exit()

if client_port >= 65536:
    print(f"Client Port (%d) should be less than 65536" % client_port)
    exit()

if recipe_name == "":
    print(f"Please pass the recipe name to run")
    exit()

print(f"Server conf path: %s" % server_conf_path)
print(f"Inotify path: %s" % inotify_path)
print(f"Init directory path: %s" % init_path)
print(f"Number of Servers: %s" % npeers)
print(f"Port no:%s" % port)
print(f"Client Port no:%s" % client_port)
print(f"Recipe: %s" % recipe_name)

# Creare Cluster object
clusterobj = NiovaCluster(npeers)

genericcmdobj = GenericCmds() 
raftconfobj = RaftConfig(server_conf_path)

raftconfobj.export_path()
raftconfobj.generate_raft_conf(genericcmdobj, npeers, "127.0.0.1", port,
                                client_port, inotify_path)
print(f"Raft conf and server configs generated")

inotifyobj = InotifyPath(inotify_path, True)

inotifyobj.export_init_path(init_path)

clusterobj.raft_conf_obj_store(raftconfobj)

clusterobj.inotify_obj_store(inotifyobj)

recipe_arr = []

'''
Iterate over the recipe hierarchy and gather the recipe objects.
'''

RecipeModule = importlib.import_module(recipe_name)
print(RecipeModule)

RecipeClass = RecipeModule.Recipe

recipe_arr.append(RecipeClass)
parent = RecipeClass().pre_run()

'''
Call pre_run method of all recipes in the hierarchy to build the recipe
tree for execution.
'''
while parent != "":
    parentRecipeModule = importlib.import_module(parent)

    RecipeClass = parentRecipeModule.Recipe
    recipe_arr.append(RecipeClass)
    parent = RecipeClass().pre_run()

print(f"Recipe Hierarchy from Root => Leaf")
for r in reversed(recipe_arr):
    print(f"%s=> " % r().name)

if dry_run:
    print("Dry Run recipes")
    for r in reversed(recipe_arr):
        print(f"Running Recipe %s" % r().name)
        r().dry_run()

    exit()

'''
Executing recipes from Root to Leaf order.
'''
for r in reversed(recipe_arr):
    print(f"Running Recipe %s" % r().name)
    r().run(clusterobj)

'''
Calling post_run method in the reverse order i.e Leaf to Root for
cleaning up the files/processes which that specific recipe had created/started.
'''
print("Call post_run to cleanup from leaf recipe to root recipe")

for r in recipe_arr:
    print(f"Post Run Recipe: %s" % r().name)
    r().post_run(clusterobj)


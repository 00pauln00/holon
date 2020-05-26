import os, sys, importlib, getopt
from raftconfig import RaftConfig
from inotifypath import InotifyPath
from niovacluster import NiovaCluster

def Usage():
    print("-s <server config path>\n"
          "-n <Inotify path>\n"
          "-i <Init command path>\n"
          "-o <Number of Servers>\n"
          "-p <Port>\n"
          "-c <Client Port>\n"
          "-r <Recipe Name>\n"
          "-h Print Help")
try:
    options, args = getopt.getopt(
            sys.argv[1:], "s:n:i:o:p:c:r:h",["server_conf_path=",
                        "inotify_path=", "init_path=", "npeers=", 
                        "port=", "client_port=", "recipe=", "help"])
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
        if name in ('-h', "--help"):
            Usage()
            sys.exit(0)

except getopt.GetoptError:
    Usage()
    sys.exit(1) 

print(f"Server conf path: %s" % server_conf_path)
print(f"Inotify path: %s" % inotify_path)
print(f"Init directory path: %s" % init_path)
print(f"Number of Servers: %s" % npeers)
print(f"Port no:%s" % port)
print(f"Client Port no:%s" % client_port)
print(f"Running Recipe: %s" % recipe_name)

# Creare Cluster object
clusterobj = NiovaCluster(npeers)

raftconfobj = RaftConfig(server_conf_path)

raftconfobj.export_path()
raftconfobj.generate_raft_conf(npeers, "127.0.0.1", port, client_port, inotify_path)

inotifyobj = InotifyPath(inotify_path, True)

inotifyobj.export_init_path(init_path)

clusterobj.raft_conf_obj_store(raftconfobj)

clusterobj.inotify_obj_store(inotifyobj)

recipe_arr = []
print(f"Leaf recipe %s" % recipe_name)

print(f"Iterate over the recipe hierarchy and gather the recipe objects")
RecipeModule = importlib.import_module(recipe_name)
print(RecipeModule)

RecipeClass = RecipeModule.Recipe

recipe_arr.append(RecipeClass)
parent = RecipeClass().pre_run()

while parent != "":
    parentRecipeModule = importlib.import_module(parent)

    RecipeClass = parentRecipeModule.Recipe
    recipe_arr.append(RecipeClass)
    parent = RecipeClass().pre_run()

print("Run the actual recipe from Root to leaf")

for r in reversed(recipe_arr):
    print(f"Running Recipe %s" % r().name)
    r().run(clusterobj)

print("Call post_run to cleanup from leaf recipe to root recipe")
for r in recipe_arr:
    print(f"Post Run Recipe: %s" % r().name)
    r().post_run(clusterobj)


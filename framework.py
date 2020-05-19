import os, sys, importlib

recipe_arr = []
recipe_name = sys.argv[1]
print(f"Run recipe %s" % recipe_name)

print(f"Iterate over the recipe hierarchy and gather the recipe objects")
RecipeModule = importlib.import_module(recipe_name)
print(RecipeModule)

RecipeClass = RecipeModule.Recipe

recipe_arr.append(RecipeClass)
print(f"Pre run Recipe: %s" % RecipeClass().name)
parent = RecipeClass().pre_run()

while parent != "":
	parentRecipeModule = importlib.import_module(parent)

	RecipeClass = parentRecipeModule.Recipe
	recipe_arr.append(RecipeClass)
	print(f"Pre run Recipe: %s" % RecipeClass().name)
	parent =  RecipeClass().pre_run()

print("Run the actual recipe from Root to leaf")

for r in reversed(recipe_arr):
	print(f"Running Recipe %s" % r().name)
	r().run()

print("Call post_run to cleanup from leaf recipe to root recipe")
for r in recipe_arr:
	print(f"Post Run Recipe: %s" % r().name)
	r().post_run()

from recipe01 import Recipe as recipe01
import os, importlib

rec01 = recipe01()

# Get parent of recipe01

parent = rec01.get_parent()
desc = rec01.desc

parentRecipeModule = importlib.import_module(parent)
print(parentRecipeModule)
parentRecipeClass = parentRecipeModule.Recipe
print(parentRecipeClass)
parentRecipeObject = parentRecipeClass()
print(parentRecipeObject)

print(f"Parent is: %s" % parent)
print(f"Desc is : %s" % desc)

print(parentRecipeObject)
print(parentRecipeObject.name)

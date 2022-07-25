import json
import copy, random

file_name = "log.txt"
order = ["ok", "failed", "skipped", "rescued"]

temp_dict = {}
jsondata = {}
structure = {}

def parse_play_recap(file):
    #Read log file line by line
    i = 0
    for line in file.readlines():

        if '----' in line:

           splitLine = line.split()
           del splitLine[:6]
           del splitLine[-2]
           time = " ".join(splitLine[-1:])
           tasks = splitLine[:-1]
           tasks = " ".join(tasks)
           tasks = tasks.replace(":", "")
           tasks = tasks.replace("  ", " ")
           tasks = tasks.replace(" ", "_")

           i += 1
           temp_dict['task' + str(i) + '_' + tasks] = float(time[:-1])

        elif '####' and 'recipe_name' in line:
            recipe = line.split()
            del recipe[:1]
            recipeJoin = "".join(recipe)
            splitRecipe = recipeJoin[:-4]
            splitRecipe = splitRecipe.replace("_", " ")

            recipeName = splitRecipe.replace("#", "")
            recipeName = recipeName[:-4].replace(" ", "_")

            i = 0
            jsondata[recipeName] = {}
            jsondata[recipeName]['tasks'] = copy.deepcopy(temp_dict)
            jsondata[recipeName]['summary'] = copy.deepcopy(structure)

            temp_dict.clear()

        elif 'unreachable' in line:
           details = line.split()
           del details[:8]
           del details[1]
           del details[1]
           del details[4]
           details = [i.split('=')[-1] for i in details]
           details = [x.strip() for x in details]
           structure = {key:int(value) for key, value in zip(order, details)}

    output = json.dumps(jsondata, indent=4)

    return output

#Open log file to read
file = open(file_name, "r")

#Call function here
output = parse_play_recap(file)

# Writing to recipe_summary.json
with open("recipe_summary.json", "w") as outfile:
    outfile.write(output)

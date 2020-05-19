import os

class Recipe:
	def __init__(self):
		self.name = "recipe04"
		self.desc = "Stage 4"
		self.parent = "recipe03"

	def pre_run(self):
		return self.parent

	def run(self):
		# start the while loop
		print(f"Starting process from Recipe: %s" % self.name)

	def post_run(self):
		# Kill the loop
		print(f"Stopping process from Recipe: %s" % self.name)

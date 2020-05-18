import os

class Recipe:
	def __init__(self):
		self.name = "recipe01"
		self.desc = "Pause processes"
		self.parent = "recipe00"

	def get_parent(self):
		return self.parent

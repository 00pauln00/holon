import os

class Recipe:
	def __init__(self):
		self.name = "recipe00"
		self.desc = "Bootup cluster"
		self.parent = ""

	def get_parent(self):
		return self.parent

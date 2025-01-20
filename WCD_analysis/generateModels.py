import sys

# Conda enviroment paths
sys.path.append('/home/vicente/anaconda3/envs/freecad-env/lib')
sys.path.append('/home/vicente/anaconda3/envs/freecad-env/Mod/Fem')

import numpy as np
import FreeCAD
import Part

def SqrWCD(width, wall_thickness):

	half_length = 0.5 * width
	height = np.sqrt(2) * half_length / np.tan(np.radians(41.2))
	
	print(f'[SQR] width: {width}; w_t: {wall_thickness}; height: {height}')
	inner_box = Part.makeBox(width, width, height)

	outer_box = Part.makeBox(
        width + 2 * wall_thickness, 
        width + 2 * wall_thickness, 
        height + 2 * wall_thickness
    )

	inner_box.translate(FreeCAD.Vector(wall_thickness, wall_thickness, wall_thickness))
	WCD_model = outer_box.cut(inner_box)
	WCD_model.translate(FreeCAD.Vector(-half_length-wall_thickness, -half_length-wall_thickness, 0))

	return WCD_model

def HexWCD(width, wall_thickness):

	radius = 0.5 * width
	height = radius / np.tan(np.radians(41.2))

	print(f'[HEX] width: {width}; w_t: {wall_thickness}; height: {height}')

	def hexWire(radius, z=0):
		vertices = []
		for i in range(6):
			angle = np.radians(60 * i)
			x = radius * np.cos(angle)
			y = radius * np.sin(angle)
			vertices.append(FreeCAD.Vector(x, y, z))
		vertices.append(vertices[0])
		return Part.makePolygon(vertices)

	outer_wire = hexWire(radius + wall_thickness)
	outer_face = Part.Face(outer_wire)
	outer_solid = outer_face.extrude(FreeCAD.Vector(0, 0, height + 2 * wall_thickness))

	inner_wire = hexWire(radius)
	inner_face = Part.Face(inner_wire)
	inner_solid = inner_face.extrude(FreeCAD.Vector(0, 0, height))
	inner_solid.translate(FreeCAD.Vector(0, 0, wall_thickness))

	WCD_model = outer_solid.cut(inner_solid)

	return WCD_model

def CirWCD(width, wall_thickness):

	radius = 0.5 * width
	height = radius / np.tan(np.radians(41.2))

	print(f'[CIR] width: {width}; w_t: {wall_thickness}; height: {height}')

	inner_cylinder = Part.makeCylinder(radius, height)
	inner_cylinder.translate(FreeCAD.Vector(0, 0, wall_thickness))

	outer_cylinder = Part.makeCylinder(radius + wall_thickness, height + 2 * wall_thickness)

	WCD_model = outer_cylinder.cut(inner_cylinder)

	return WCD_model

#################################################################################################

WIDTH = [3e3, 3.5e3, 4e3, 4.5e3, 5e3, 5.5e3] # [mm]

if __name__ == '__main__':

	doc = FreeCAD.newDocument('Exporter')

	for width in WIDTH:

		width = int(width)
		
		#sqrWCD = SqrWCD(width, 12)
		hexWCD = HexWCD(width, 12)
		#cirWCD = CirWCD(width, 12)
		
		#obj_sqr = doc.addObject('Part::Feature', 'SqrWCD')
		#obj_sqr.Shape = sqrWCD
		obj_hex = doc.addObject('Part::Feature', 'HexWCD')
		obj_hex.Shape = hexWCD
		#obj_cir = doc.addObject('Part::Feature', 'CirWCD')
		#obj_cir.Shape = cirWCD

		doc.recompute()

		#output_path_sqr = f'files/sqr_{width}/sqr_{width}.step'
		output_path_hex = f'files/hex_{width}/hex_{width}.step'
		#output_path_cir = f'files/cir_{width}/cir_{width}.step'

		print(output_path_hex)

		#Part.export([obj_sqr], output_path_sqr)
		Part.export([obj_hex], output_path_hex)
		#Part.export([obj_cir], output_path_cir)

		#print(f'Squared-base Cherenkov Detector exported as   : {output_path_sqr}')
		print(f'Hexagonal-base Cherenkov Detector exported as : {output_path_hex}')
		#print(f'Circular-base Cherenkov Detector exported as  : {output_path_cir}')
		print('#'*76)
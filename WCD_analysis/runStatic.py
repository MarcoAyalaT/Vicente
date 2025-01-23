import sys

# Conda enviroment paths
sys.path.append('/home/vicente/anaconda3/envs/freecad-env/lib')
sys.path.append('/home/vicente/anaconda3/envs/freecad-env/Mod/Fem')

import numpy as np
import ObjectsFem
import FreeCAD
import Part
import Mesh
import time
import yaml
import Fem
import os

from femmesh.gmshtools import GmshTools
from numpy import tan, radians as rad
from femtools import ccxtools
from dotmap import DotMap

with open('configStatic.yaml', 'r') as file:
	data = yaml.safe_load(file)
	config = DotMap(data)

WIDTH = [int(1.25e3)]
BASE = ['hex', 'cir']

use_old_FCStd = config.CONFIG.useExistingFiles
use_old_mesh = config.CONFIG.useExistingMesh

for base in BASE:
	for width in WIDTH:

		start = time.time()

		doc_name = f'{base}_{width}'
		print('―'*70 + '| RUNNING ' + doc_name + ' |')

		if os.path.exists(f'files/{doc_name}/{doc_name}_mech.FCStd') and use_old_FCStd:
			print('[INFO]: Skipped file generation, using old FCStd file instead')
			continue

		if 'hex' in doc_name:
			height = 0.5 * width / tan(rad(41.2))
			OUTER_BOTTOM = config.FACE_CONSTRAINT_FIXED.hex
			INNER_WALLS = config.FACES_CONSTRAINT_PRESSURE.hex

		elif 'cir' in doc_name:	
			height = 0.5 * width / tan(rad(41.2))
			OUTER_BOTTOM = config.FACE_CONSTRAINT_FIXED.cir
			INNER_WALLS = config.FACES_CONSTRAINT_PRESSURE.cir

		elif 'sqr' in doc_name:	
			height = np.sqrt(2) * 0.5 * width / tan(rad(41.2))
			OUTER_BOTTOM = config.FACE_CONSTRAINT_FIXED.sqr
			INNER_WALLS = config.FACES_CONSTRAINT_PRESSURE.sqr

		doc = FreeCAD.newDocument('Main')
		doc.FileName = f'files/{doc_name}/{doc_name}_mech.FCStd'

		doc.recompute()

		shape = Part.read(f'files/{doc_name}/{doc_name}.step')
		part = doc.addObject('Part::Feature', 'Container')
		part.Shape = shape

		doc.recompute()

		analysis_obj = ObjectsFem.makeAnalysis(doc, 'Analysis')
		analysis_obj.NoTouch = True

		doc.recompute()
		
		material_obj = ObjectsFem.makeMaterialSolid(doc, 'Steel-Stainless')
		mat = material_obj.Material
		mat['Name'] = 'Steel-Stainless'
		mat['YoungsModulus'] = '200 GPa'
		mat['PoissonRatio'] = '0.29'
		mat['Density'] = '8000 kg/m^3'
		material_obj.Material = mat
		analysis_obj.addObject(material_obj)
		
		doc.recompute()

		fixed_constraint = ObjectsFem.makeConstraintFixed(doc)
		fixed_constraint.References = [(part, OUTER_BOTTOM)]
		analysis_obj.addObject(fixed_constraint)

		doc.recompute()

		height_meter = 1e-3 * height
		pressure = config.CONSTANTS.waterDensity * config.CONSTANTS.gravityConstant * height_meter
		pressure_constraint = ObjectsFem.makeConstraintPressure(doc)
		pressure_constraint.References = [(part, wall) for wall in INNER_WALLS]
		pressure_constraint.Pressure = pressure * 1e-3
		pressure_constraint.Reversed = False
		analysis_obj.addObject(pressure_constraint)


		print(f'[INFO]: Pressure applied at every inner face: {pressure*1e-3:.4f} [kPa]')

		doc.recompute()

		gravity_constraint = ObjectsFem.makeConstraintSelfWeight(doc)
		analysis_obj.addObject(gravity_constraint)

		doc.recompute()

		solver_obj = ObjectsFem.makeSolverCalculiXCcxTools(doc)
		solver_obj.BeamShellResultOutput3D = True
		solver_obj.WorkingDir = f'data/{doc_name}/'
		analysis_obj.addObject(solver_obj)

		doc.recompute()

		########################################################################### GENERATING FEMMESH ####

		start_mesh = time.time()

		femmesh_obj = ObjectsFem.makeMeshGmsh(doc)

		if os.path.exists(f'files/{doc_name}/{doc_name}.unv') and use_old_mesh:
			print('[INFO]: Using old mesh')
			femmesh = Fem.FemMesh()
			femmesh.read(f'files/{doc_name}/{doc_name}.unv')
			femmesh_obj.FemMesh = femmesh

		else:
			femmesh_obj.CharacteristicLengthMin = config.MESH.CharacteristicLengthMin
			femmesh_obj.CharacteristicLengthMax = config.MESH.CharacteristicLengthMax
			femmesh_obj.Shape = part
			gmsh_mesh = GmshTools(femmesh_obj, analysis=analysis_obj)
			error = gmsh_mesh.create_mesh()
			if error:
				print(f'[Error]: {error}', end='')
				continue
			femmesh_obj.FemMesh.write(f'files/{doc_name}/{doc_name}.unv')
		
		analysis_obj.addObject(femmesh_obj)

		end_mesh = time.time()

		print(f'[INFO]: Mesh generated in {end_mesh-start_mesh:.2f} [s]')

		######################################################################### RUNNING THE ANALYSIS ####

		doc.recompute()

		start_fea = time.time()

		fea = ccxtools.FemToolsCcx(solver=solver_obj)

		fea.purge_results()
		fea.reset_all()
		fea.update_objects()
		fea.check_prerequisites()
		fea.run()
		
		end_fea = time.time()
		print(f'[INFO]: FEA solved in {end_fea-start_fea:.2f} [s]')

		doc.save()

		FreeCAD.closeDocument(doc.Name)

		del fixed_constraint, gravity_constraint, material_obj, shape
		del doc, fea, analysis_obj, femmesh_obj, solver_obj, pressure_constraint

		end = time.time()

		print(f'[INFO]: Completed in {end-start:.2f} [s]')

		if config.CONFIG.runFirstOnly:
			exit()













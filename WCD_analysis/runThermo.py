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

with open('configThermo.yaml', 'r') as file:
	data = yaml.safe_load(file)
	config = DotMap(data)

WIDTH = [3000, 3500, 4000, 4500, 5000, 5500]
BASE = ['hex']

use_old_FCStd = config.CONFIG.useExistingFiles
use_old_mesh = config.CONFIG.useExistingMesh

for base in BASE:
	for width in WIDTH:

		start = time.time()

		doc_name = f'{base}_{width}'
		print('―'*70 + '| RUNNING ' + doc_name + ' |')

		if os.path.exists(f'files/{doc_name}/{doc_name}_therm.FCStd') and use_old_FCStd:
			print('[INFO]: Skipped file generation, using old FCStd file instead')
			continue

		if 'hex' in doc_name:
			OUTER_TOP = config.FACE_IRRADIATED.hex
			OUTER_BOTTOM = config.FACE_CONSTRAINT_FIXED.hex

		elif 'cir' in doc_name:
			OUTER_TOP = config.FACE_IRRADIATED.cir
			OUTER_BOTTOM = config.FACE_CONSTRAINT_FIXED.cir

		elif 'sqr' in doc_name:
			OUTER_TOP = config.FACE_IRRADIATED.sqr
			OUTER_BOTTOM = config.FACE_CONSTRAINT_FIXED.sqr

		doc = FreeCAD.newDocument('Main')
		doc.FileName = f'files/{doc_name}/{doc_name}_therm.FCStd'

		doc.recompute()

		shape = Part.read(f'files/{doc_name}/{doc_name}.step')
		part = doc.addObject('Part::Feature', 'Container')
		part.Shape = shape

		doc.recompute()

		analysis_obj = ObjectsFem.makeAnalysis(doc, 'Analysis')
		analysis_obj.NoTouch = True

		doc.recompute()

		material_obj = ObjectsFem.makeMaterialSolid(doc)
		mat = material_obj.Material
		mat['Name'] = 'Steel-Stainless'
		mat['YoungsModulus'] = '200 GPa'
		mat['PoissonRatio'] = '0.29'
		mat['Density'] = '8000 kg/m^3'
		mat['ThermalConductivity'] = '16.200 W/m/K'
		mat['ThermalExpansionCoefficient'] = '17.300 µm/m/K'
		mat['SpecificHeat'] = '591.00 J/kg/K'
		material_obj.Material = mat
		analysis_obj.addObject(material_obj)

		doc.recompute()

		fixed_constraint = ObjectsFem.makeConstraintFixed(doc)
		fixed_constraint.References = [(part, OUTER_BOTTOM)]
		analysis_obj.addObject(fixed_constraint)

		doc.recompute()

		initial_temp = ObjectsFem.makeConstraintInitialTemperature(doc)
		initial_temp.initialTemperature = config.TEMPERATURE.ambientTemp
		analysis_obj.addObject(initial_temp)

		doc.recompute()

		temp_constraint = ObjectsFem.makeConstraintHeatflux(doc)
		temp_constraint.References = [(part, OUTER_TOP)]
		temp_constraint.ConstraintType = 'DFlux'
		temp_constraint.DFlux = config.HEAT_FLUX.solarHeatFlux
		analysis_obj.addObject(temp_constraint)

		doc.recompute()

		solver_obj = ObjectsFem.makeSolverCalculiXCcxTools(doc)
		solver_obj.AnalysisType = 'thermomech'
		solver_obj.ThermoMechSteadyState = False
		solver_obj.IterationsUserDefinedTimeStepLength = True
		solver_obj.TimeEnd = config.TIME.timeEnd
		solver_obj.TimeInitialStep = config.TIME.timeStep
		solver_obj.TimeMaximumStep = config.TIME.timeStep
		solver_obj.TimeMinimumStep = config.TIME.timeStep
		
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
			femmesh_obj.FemMesh.Part = part
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
		prerequisites_log = fea.check_prerequisites()
		prerequisites_log = prerequisites_log.replace("\n", " ")
		fea.run()
		
		print(f'[INFO]: {prerequisites_log}', end='\n')

		end_fea = time.time()
		print(f'[INFO]: FEA solved in {end_fea-start_fea:.2f} [s]')

		#doc.save()

		FreeCAD.closeDocument(doc.Name)

		del doc, fea, analysis_obj, femmesh_obj, solver_obj

		end = time.time()

		print(f'[INFO]: Completed in {end-start:.2f} [s]')

		if config.CONFIG.runFirstOnly:
			exit()
































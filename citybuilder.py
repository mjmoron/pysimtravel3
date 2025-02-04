from time import sleep
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.colors as colors
import random
from collections import namedtuple
from typing import List
import traceback

class Parameters:
	def __init__(self):
		self.verticalBlocks=2
		self.horizontalBlocks=2
		self.numberCarsPerBlock=10
		self.numberStations=4
		self.numberChargingPerStation=1
		self.carMovesFullDeposity=1000
		self.carRechargePerTic=10
		self.opmitimizeCSSearch=10 # bigger is more slow

		self.viewDrawCity=True

class ChargingStation:
	def __init__(self,p,grid,coordinates ,numberCharging):
		self.p=p
		self.grid=grid
		cell=self.grid.grid[coordinates[0],coordinates[1]]
		self.cell=cell
		cell.cs=self
		self.numberCharging=numberCharging
		self.queue=[]
		self.car=[None for i in range(numberCharging)]

		self.insertInRouteMap(cell)
	
	def moveCS(self):
		if len(self.queue)==0:
			return
		# Spanish: Si hay un coche en la cola, y hay un hueco en la estación, entonces el coche entra en la estación
		# English: If there is a car in the queue, and there is a gap in the station, then the car enters the station
		while 0<len(self.queue) and None in self.car:
			car=self.queue.pop(0)
			i=self.car.index(None)
			self.car[i]=car

		# Spanish: Recarga los coches que están en el cargador
		# English: Recharge the cars that are in the charger
		candidateToLeave=-1
		for i in range(self.numberCharging):
			if self.car[i]!=None:
				self.car[i].moves+=self.p.carRechargePerTic
				#print("Recharge percent:",self.car[i].moves/self.p.carMovesFullDeposity*100,"%")
				if self.car[i].moves>self.p.carMovesFullDeposity:
					self.car[i].moves=self.p.carMovesFullDeposity
					candidateToLeave=i
		#candidateToLeave=-1
		if 0<=candidateToLeave and self.cell.car==None:
			car=self.car[candidateToLeave]
			self.car[candidateToLeave]=None
			car.charging=False
			car.target2=None
			self.cell.car=car

	def insertInRouteMap(self, cell):
		visited = []
		distance = 0
		current_level = [cell]

		while current_level:
			next_level = []

			for current_cell in current_level:
				visited.append(current_cell)

				if len(current_cell.destination) > 1:
					current_cell.h2cs.append(HeuristicToCS(self, distance))

				# Añadir los orígenes a la lista del siguiente nivel
				for origin in current_cell.origin:
					if origin not in visited:
						next_level.append(origin)

			# Incrementar la distancia y mover al siguiente nivel
			distance += 1
			current_level = next_level

class HeuristicToCS:
	def __init__(self,cs:ChargingStation,distance:int):
		self.cs=cs
		self.distance=distance

class Cell:    
	ONE=1
	TWO=2
	FREE = 0

	def __init__(self, initial_state):
		self.h2cs=[]
		self.state = initial_state
		self.next_state = None
		self.neighbors = [[0,0,0],[0,0,0],[0,0,0]]
		self.origin=[]
		self.destination=[]
		self.velocity=0
		self.x=-1
		self.y=-1

		self.car=None
		self.cs=None
		self.t=0

	def add_neighbor(self, neighbor):
		self.neighbors.append(neighbor)

	def set_next_state(self):
		total = sum(sum(objeto.state for objeto in fila) for fila in self.neighbors) 
		total -= self.neighbors[1][1].state
		total = total // Cell.STREET
		
		if self.state == Cell.STREET:
			if (total < 2) or (total > 3):
				self.next_state = Cell.FREE
			else:
				self.next_state = self.state
		else:
			if total == 3:
				self.next_state = Cell.STREET
			else:
				self.next_state = self.state

	def update_state(self):
		self.state = self.next_state
	
	def updateColor(self):
		count=len(self.origin+self.destination)
		if count==0:
			self.state=Cell.FREE
		elif count==1 or count==2:
			self.state=Cell.ONE
		elif count==2:
			self.state=Cell.TWO

	def update(self,t): 
		# when it is an intersection
		stop=False
		for origin in self.origin: # reversed(self.origin):
			if not stop:
				if origin.car is None:
					continue
				stop=True
			else:
				origin.t=t+1

	def color(self,city):
		cell=self
		
		if cell.state==Cell.FREE:
			return 0
		else:
			if len(cell.destination)==0 or len(cell.origin)==0:
				r=3
			elif len(cell.destination)==2:
				r=2
			else:
				r=1
		
		if cell.t==city.t+1:
			r=3
		if cell.car!=None:
			r=5
		if cell.cs!=None:
			r=4
		return r

Street = namedtuple('Street', ['path', 'velocity','lames'])

class Block:

	def __init__(self):
		r = 1
		self.lanes=[]
		self.velocities=[]
		self.sugar(
			Street([ (-1,3), (3,3), (3,-1) ], 1,2), # Rotonda
			#Street([(r,3), (r,-1)],1,2), # Cruce
			#Street([(-1,r),(3,r)],1,2),

			Street([(r,47),(r,3)],2,2), # Avenidas
			Street([(3,r),(47,r)],2,2), 

			Street([(47,15),(r+1-1,15)],1,1), # Calles #incorporación
			Street([(r+1-1,36), (47,36) ],1,1), #salida 			
			Street([ (15,r+1-1), (15,47) ],1,1),
			Street([ (36,47), (36,r+1-1), ],1,1),
		)

		max_width = 0
		max_height = 0
		for lane in self.lanes:
			for point in lane:
				if point[0] > max_width:
					max_width = point[0]
				if point[1] > max_height:
					max_height = point[1]
		self.width = (max_width+1)*2
		self.height = (max_height+1)*2

	def pathPlusLame(self,path,lame):
		name=["" for i in range(len(path))]
		for i in range(len(path)-1):
			source=path[i]
			target=path[i+1]
			if source[1]==target[1]: #vertical
				if source[0]<target[0]: #up
					key="u"
				else: #down
					key="d"
			else: #horizontal
				if source[1]<target[1]: #right
					key="r"
				else: #left
					key="l"
			name[i]+=key
			name[i+1]+=key
			
		
		switch={				
			"u":(0,1),
			"d":(0,-1),
			"r":(-1,0),
			"l":(1,0),
			"ur":(-1,1),
			"ul":(1,1),
			"dr":(1,1),
			"dl":(-1,1),
			"ru":(-1,1),
			"rd":(-1,-1),
			"lu":(1,1),
			"ld":(1,-1),
		}

		newPath=[]
		for i,p in enumerate(path):
			delta=switch[name[i]]
			newPath.append((p[0]+delta[0]*lame,p[1]+delta[1]*lame))
		return newPath

	def sugar(self,*streets):
		for street in streets:
			for lame in range(street.lames):
				self.lanes.append(self.pathPlusLame(street.path,lame))
				self.velocities.append(street.velocity)

	def draw2(self,grid,lastx,lasty,xx,yy,velocity):
		if lastx is None:
			return
		if lasty is None:
			return
		last=None
		if lastx == xx:
			inc = -1
			if lasty < yy:
				inc = 1
			for i in range(lasty,yy+inc,inc):
				current=grid.grid[i%grid.heigh,xx%grid.width]
				grid.link(last,current,velocity)
				last=current
				yield
		if lasty == yy:
			inc = -1
			if lastx < xx:
				inc = 1
			for i in range(lastx,xx+inc,inc):
				current=grid.grid[yy%grid.heigh,i%grid.width]
				grid.link(last,current,velocity)
				last=current
				yield

	def draw(self,grid,x,y):
		for i,lane in enumerate(self.lanes):
			lastx=None
			lasty=None
			for point in lane:
				xx=x+point[0]+1
				yy=y+point[1]+1
				#grid.grid[xx][yy].state=Cell.STREET
				for _ in self.draw2(grid,lastx,lasty,xx,yy,self.velocities[i]):
					yield
				lastx=xx
				lasty=yy
			lastx=None
			lasty=None
			for point in lane:
				xx=x+point[1]+1
				yy=y-point[0]-1
				#grid.grid[x+point[1]+1,y-point[0]-1].state=Cell.STREET
				for _ in self.draw2(grid,lastx,lasty,xx,yy,self.velocities[i]):
					yield
				lastx=xx
				lasty=yy
			lastx=None
			lasty=None
			for point in lane:
				xx=x-point[0]-1
				yy=y-point[1]-1
				#grid.grid[x-point[0]-1,y-point[1]-1].state=Cell.STREET
				for _ in self.draw2(grid,lastx,lasty,xx,yy,self.velocities[i]):
					yield
				lastx=xx
				lasty=yy
			lastx=None
			lasty=None
			for point in lane:
				xx=x-point[1]-1
				yy=y+point[0]+1
				#grid.grid[x-point[1]-1,y+point[0]+1].state=Cell.STREET
				for _ in self.draw2(grid,lastx,lasty,xx,yy,self.velocities[i]):
					yield
				lastx=xx
				lasty=yy
		
class City:
	def __init__(self,p, block):
		
		self.p=p
		self.block=block
		self.grid=Grid(p.verticalBlocks*block.height,p.horizontalBlocks*block.width)

		self.t=0

		city = self
		self.city_generator = city.generator()
		self.g=city.grid
		#g=Grid(100,100)

		# Animation
		next(self.city_generator)
		next(self.city_generator)

  def plotCity(self):
		fig, ax = plt.subplots()

		bounds = [0, 1, 2, 3, 4, 5, 6]
		cmap = colors.ListedColormap(['black',  'green', 'blue','red', 'yellow', 'white'])
		norm = colors.BoundaryNorm(bounds, cmap.N)
	

		def extract_color(cell_obj):
			return cell_obj.color(self)

		img = ax.imshow(np.vectorize(extract_color)(self.g.grid), interpolation='nearest', cmap=cmap, norm=norm)
		self.ani = animation.FuncAnimation(fig, self.update, fargs=(img, self.g.grid, self.g.heigh,self.g.width, ), frames=50,interval=1)
		plt.show()

		
		
	
	def update(self,frameNum, img, grid, heigh, width):
		try:
			#for i in range(100):
			next(self.city_generator)
		except StopIteration:
			pass
		except Exception as e:
			print(e)
			pass

		# for i in range(heigh):
		#     for j in range(width):
		#         grid[i, j].set_next_state()

		newGrid = np.empty((heigh, width))
		for i in range(heigh):
			for j in range(width):
				#grid[i, j].update_state()
				newGrid[i, j] = grid[i, j].color(self)
				# if newGrid[i, j] == Cell.STREET:
				# 	print(i,j)
				
		# initial_states = np.random.choice([Cell.STREET, Cell.FREE], grid.shape[0]*grid.shape[1] , p=[0.2, 0.8])
		# newGrid = np.array([state for state in initial_states]).reshape(grid.shape[0], grid.shape[1])
		img.set_data(newGrid)
		return img,


	def generator(self):
		try:
			# Build city streets
			yieldCada=1000
			if self.p.viewDrawCity:
				yieldCada=1
			yieldI=0
			for i in range(self.p.verticalBlocks):
				for j in range(self.p.horizontalBlocks):
					for _ in self.block.draw(self.grid,i*self.block.height+self.block.height//2,j*self.block.width+self.block.width//2):
						if yieldCada<=yieldI:
							yieldI=0
							yield
						yieldI+=1

			numberBlocks=self.p.verticalBlocks*self.p.horizontalBlocks
			numberCarsPerBlock=self.p.numberCarsPerBlock
			numberStations=self.p.numberStations
			numberChargingPerStation=self.p.numberChargingPerStation

      # Put cs (Charge Stations)
			self.cs=[]
			for _ in range(numberStations): #*self.verticalBlocks*self.horizontalBlocks): # number of cs
				self.cs.append(ChargingStation(self.p,self.grid,self.grid.randomStreet(),numberChargingPerStation))
				if yieldCada<=yieldI:
					yieldI=0
					yield
				yieldI+=1


			# Orden and filter cs by p.opmitimizeCSSearch
			for cell in self.grid.grid.flatten():
				if 0<len(cell.h2cs):
					cell.h2cs.sort(key=lambda x: x.distance)
					cell.h2cs=cell.h2cs[:self.p.opmitimizeCSSearch]

			# Put cars
			self.cars=[]
			for _ in range(numberCarsPerBlock*numberBlocks): # number of cars
				self.cars.append(Car(self.p,self.grid,self.grid.randomStreet(),self.grid.randomStreet()))
				if yieldCada<=yieldI:
					yieldI=0
					yield
				yieldI+=1

			# Simulation
			while True:
				self.t+=1
				moreMove=self.cars
				noMove=[]
				while True:
					moreMove2=[]
					for car in moreMove:
						move=car.moveCar(self.t)
						if move:
							moreMove2.append(car)
						else:
							noMove.append(car)
					if len(moreMove2)==0:
						break
					moreMove=moreMove2
					for inter in self.grid.intersections:
						inter.update(self.t)

				for cs in self.cs:
					cs.moveCS()

				self.cars=noMove

				yieldCada=1
				if yieldCada<=yieldI:
					yieldI=0
					yield
				yieldI+=1

		except Exception as e:  # Esto captura cualquier excepción derivada de la clase base Exception
			print(traceback.format_exc())  # Esto imprime la traza completa del error

class Grid:
	def __init__(self, heigh, width):
		self.width = width
		self.heigh = heigh
		self.intersections = []
		initial_states = np.random.choice([Cell.FREE], width*heigh, p=[1])
		self.grid = np.array([Cell(state) for state in initial_states]).reshape(heigh, width)
		for i in range(heigh):
			for j in range(width):
				self.grid[i, j].x=j
				self.grid[i, j].y=i
				for di in [-1, 0, 1]:
					for dj in [-1, 0, 1]:
						self.grid[i, j].neighbors[di+1][dj+1]=self.grid[(i+di)%heigh, (j+dj)%width]
	def distance(self,x0,y0,x1,y1):
		# latince distance
		dx = abs(x1 - x0)
		dy = abs(y1 - y0)
		if dx > self.width / 2:
			dx = self.width - dx
		if dy > self.heigh / 2:
			dy = self.heigh - dy
		return dx + dy
	
	def randomStreet(self):
		while True:
			x = random.randint(0,self.width-1)
			y = random.randint(0,self.heigh-1)
			cell=self.grid[y][x]
			if cell.state!=Cell.FREE and cell.car==None:
				return (y,x)
	def link(self,origin,target,velocity):
		if origin!=None:
			target.origin.append(origin)
			origin.destination.append(target)
			target.updateColor()
			origin.updateColor()
			target.velocity=velocity
			origin.velocity=velocity
			if len(target.origin)>1:
				self.intersections.append(target)

class Car:
	def __init__(self,p : Parameters, grid: Grid, xy,targetCoordiantes:tuple):
		self.p=p
		self.grid = grid
		self.x = xy[0]
		self.y = xy[1]

		self.target=self.grid.grid[targetCoordiantes[0],targetCoordiantes[1]]
		self.target2=None # if need to recharge
		self.grid.grid[self.y, self.x].car = self
		self.queda=0
		# Change V2 to V3. Why use normal? A normal is a sum of uniform distributions. The normal is not limited to [0,1] but the uniform is. The normal by intervals.
		self.moves=p.carMovesFullDeposity*random.random() 

		# initial moves must be enough to reach the CS at least
		dis,_=self.localizeCS(self.grid.grid[self.y,self.x])	
		if self.moves<dis:
			self.moves=dis
		self.charging=False

	def inTarget(self,target):
		return self.grid.grid[self.y,self.x]==target
	
	def localizeCS(self,cell:Cell,distance=0):
		if cell.cs!=None:
			return (0,cell.cs)
		if len(cell.h2cs)==0:
			if len(cell.destination)==1:
				return self.localizeCS(cell.destination[0],distance+1)
			else:
				print("Error: in data structure of CS")
		aux=cell.h2cs[0]
		return (distance+aux.distance,aux.cs)
	
	def moveCar(self,t):
		if self.inTarget(self.target):
			(y,x)=self.grid.randomStreet()
			self.target=self.grid.grid[y,x]
		if self.inTarget(self.target2):
			# enter on CS
			if not self.charging:
				cs=self.target2.cs
				self.target2.cs.queue.append(self)
				self.target2.car=None
				self.charging=True
			return
		
		cell=self.grid.grid[self.y,self.x]
		if t!=cell.t:
			self.queda=cell.velocity
		cell.t=t
		if len(cell.destination)==1:
			toCell=cell.destination[0]
			if toCell.t==t or toCell.car!=None:
				return False #ocupado por otro
			self.x = toCell.x
			self.y = toCell.y
			cell.car = None
			toCell.car = self
			toCell.t=t
			self.moves-=1
		else:
			dis,ire=self.aStart(cell,self.target)
			dis2,_=self.localizeCS(ire)
			if self.moves<dis+dis2:
				# There are not enough moves, need to recharge in CS first
				dis3,cs=self.localizeCS(cell)
				if self.moves<dis3:
					# There are not enough moves, event with recharge in CS
					#return False
					pass
				ire=self.aStart(cell,cs.cell)[1]
				self.target2=cs.cell
			if ire.t==t or ire.car!=None:
				return False
			self.x = ire.x
			self.y = ire.y
			cell.car = None
			ire.car = self
			ire.t=t
			self.moves-=1
	
		self.queda-=1
		if self.queda==0:
			return False
		return True

	def aStartDistance(self,cell:Cell,target:Cell):
		# Distance version
		# only mark visited if it has more than one destination
		visited=set()
		visited.add(cell)
		opened={}
		for d in cell.destination:
			opened[d]=d
		opened2={}
		distancia=1
		while True:
			# solo se añaden los visited con mas de uno
			for (o,r) in opened.items():
				if o==target:
					return (distancia,opened[o])
				if len(o.destination)==1:
					opened2[o.destination[0]]=r
				else:
					if o not in visited:
						visited.add(o)
						for d in o.destination:
							opened2[d]=r
			opened=opened2
			opened2={}
			distancia+=1

	def aStartTime(self,cell:Cell,target:Cell):
		# Time version
		# only mark visited if it has more than one destination
		visited={}
		visited.add(cell)
		opened={}
		for d in cell.destination:
			opened[d]=d
		opened2={}
		distancia=1
		while True:
			# solo se añaden los visited con mas de uno
			for (o,r) in opened.items():
				if o==target:
					return (distancia,opened[o])
				if len(o.destination)==1:
					opened2[o.destination[0]]=r
				else:
					if o not in visited:
						visited.add(o)
						for d in o.destination:
							opened2[d]=r
			opened=opened2
			opened2={}
			distancia+=1

class TimeNode:
	pass

p=Parameters()
c=City(p,Block())
c.plotCity()

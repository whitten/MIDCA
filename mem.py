
from MIDCA.logging import Event
import threading

class Memory:
	
	'''
	To do: in theory, a lock could be deleted in between when its existence is checked
	and when it is acquired. At some point this needs to be fixed.
	'''
	
	#if necessary for efficiency, these keys should be numbers or enum constants.
	STATES = "__world states"
	STATE = "__current state"
	GOAL_GRAPH = "__goals"
	CURRENT_GOALS = "__current goals"
	PLANS = "__plans"
	ACTIONS = "__actions"
	FEEDBACK = "__feedback"
	#ROS constants used by rosrun classes and related modules in act and perceive.
	ROS_OBJS_DETECTED = "__detected object queue"
	ROS_OBJS_STATE = "__state"
	CALIBRATION_MATRIX = "__camera calibration status"
	CALIBRATION_Z = "__Z"
	STACK_Z = "__SZ"
	UNSTACK_Z = "__UZ"
	RAISING_POINT = "__RP"
	PUTTING_POINT = "__PP"
	ROS_WORDS_HEARD = "__words heard queue"
	ROS_FEEDBACK = "__ros feedback"
	Objects = "__objects"
	
	def __init__(self, args = {}):
		self.knowledge = {}
		self.update(args)
		self.logger = None
		self.mainLock = threading.Lock() #to synchronize lock creation
		self.locks = {} #lock for each key

	#Handles structs with custom update methods, dict update by dict or tuple, list append, and simple assignment.
	def _update(self, structname, val):
		with self.mainLock:
			if structname not in self.locks:
				self.locks[structname] = threading.Lock()
		with self.locks[structname]:
			if not structname in self.knowledge:
				self.knowledge[structname] = val
			elif self.knowledge[structname].__class__.__name__ == "dict":
				if val.__class__.__name__ == "dict":
					self.knowledge[structname].update(val) #update dict with dict
				elif len(val) == 2:
					self.knowledge[structname][val[0]] = val[1] #update dict with tuple
			elif hasattr(self.knowledge[structname], "update"):
				self.knowledge[structname].update(val) #generic update
			else:
				self.knowledge[structname] = val #assignment
			self.logAccess(structname)
	
	def add(self, structname, val):
		'''
		Used to create lists of items. If nothing is stored under structname, will create
		a one-item list containing val. If there is a list, will append val. If some item
		is stored with no append method, will create a two-item list with the previously
		stored item and val.
		'''
		with self.mainLock:
			if structname not in self.locks:
				self.locks[structname] = threading.Lock()
		with self.locks[structname]:
			if not structname in self.knowledge:
				self.knowledge[structname] = [val]
			elif hasattr(self.knowledge[structname], "append"):
				self.knowledge[structname].append(val)
			else:
				self.knowledge[structname] = [self.knowledge[structname], val]
			self.logAccess(structname)
	
	def set(self, structname, val):
		with self.mainLock:
			if structname not in self.locks:
				self.locks[structname] = threading.Lock()
		with self.locks[structname]:
			self.knowledge[structname] = val
			self.logAccess(structname)
	
	def update(self, args):
		for structname, val in args.items():
			self._update(structname, val)
	
	def update_all(self, structname, val):
		with self.mainLock:
			if structname not in self.locks:
				self.locks[structname] = threading.Lock()
		with self.locks[structname]:
			if structname in self.knowledge and (not isinstance(self.knowledge[structname], basestring)):
				struct = self.knowledge[structname]
				if hasattr(struct, "__getitem__") or hasattr(struct, "__iter__"):
					for item in struct:
						if hasattr(item, "update"):
							item.update(val)
				elif hasattr(struct, "update"):
					struct.update(val)
			self.logAccess(structname)
	
	def remove(self, structname):
		with self.mainLock:
			if structname not in self.locks:
				self.locks[structname] = threading.Lock()
		with self.locks[structname]:
			self.logAccess(structname)
			if structname in self.knowledge:
				del self.knowledge[structname]
				del self.locks[structname]
	
	def clear(self):
		self.knowledge.clear()
		self.locks.clear()
	
	def get(self, structname):
		with self.mainLock:
			if structname not in self.locks:
				return None #if there is knowledge stored there must be a lock.
		with self.locks[structname]:
			self.logAccess(structname)
			if structname in self.knowledge:
				return self.knowledge[structname]
			return None
	
	def get_and_clear(self, structname):
		with self.mainLock:
			if structname not in self.locks:
				return None #if there is knowledge stored there must be a lock.
		with self.locks[structname]:
			self.logAccess(structname)
			val = self.knowledge[structname]
			del self.knowledge[structname]
			del self.locks[structname]
			return val
	
	def get_and_lock(self, structname):
		with self.mainLock:
			if structname not in self.locks:
				self.locks[structname] = threading.Lock()
				self.locks[structname].acquire()
				return None
		self.locks[structname].acquire()
		self.logAccess(structname)
		return self.knowledge[structname]
	
	def unlock(self, structname):
		try:
			self.locks[structname].release()
		except KeyError:
			pass
	
	def enableLogging(self, logger):
		self.logger = logger
	
	def logAccess(self, key):
		if self.logger:
			self.logger.logEvent(MemAccessEvent(key))

class MemAccessEvent(Event):

	def __init__(self, keyAccessed):
		self.keys = ['log', 'Memory Access']
		self.loggable = True
		self.memKey = keyAccessed
	
	def __str__(self):
		return "Memory access at key " + str(self.memKey)
	
	

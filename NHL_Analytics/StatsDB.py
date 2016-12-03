import MySQLdb
from config import CONFIG as config


class StatsDB():

	def __init__(self):
		self.db = MySQLdb.connect(passwd=config["mysql"]["pw"],host="localhost",user="root", db="halcyonnhl")
		self.cursor = self.db.cursor()

	def execute_command(self, query_string):
		self.cursor.execute(query_string)
		self.db.commit()

	def execute_query(self, query_string):
		self.cursor.execute(query_string)
		sqlOut = self.cursor.fetchall()
		return sqlOut

	def get_connection(self):
		return self.db
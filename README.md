# DemoFiles
A few files and documents demonstrating some of my work:

\1. thorn_nhl1516_db.sql.zip - A compressed sql file of an NHL database for the 20152016 season. Code for web-scraping, database construction and population, as well as conceptual framework developed by Nolan Thorn and Brendan Thorn. Contact Brendan at brendankthorn@gmail.com for any inquiries about database use.

To set up DB on your system, download and decompress file. You must have MySQL (or other SQL system) installed and configured on your machine, then try:

mysql -u username -p [your_db_name] < thorn_nhl1516_db.sql

\2. NHL_PlayerHotStreaks folder - A sample python script, which uses the above NHL DB, that prints out some stats demonstrating the non-existence of goal-scoring "hot streaks". I.E. A 20+ goal scorer is just as likely to score in a game after not scoring in the previous game as he is if he had scored in the previous game. Once you have python installed on your system, run it through the terminal (from the NHL_PlayerHotStreaks folder) with:

python PlayerHotStreaks.py

If there are any problems, make sure the config.json file has the correct MySQL configurations for your system, and that the DB is properly named in the StatsDB.py file.

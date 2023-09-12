# Neo4j

## Setup and Installation
---
* Visit [neo4j.com/download](https://neo4j.com/download/)
* Click on the DOWNLOAD button > next page > give your details > next page > copy the generated activation key (exe will start downloading)
* Start installing the software application, in the "Software Registration" stage, Add your software key and click "Activate", and the software will install smoothly.

## Quick basis
---
* We have nodes and edge in the graphs that we built
* We can give properties for nodes and edges
* We can only build directional graphs
* If it is bi-directional, we have to use two edges inplace of one edge.
* We have different labels attached the nodes to represent different entity types.

## Connecting databases
---
* We can connect our local database to the browser once we start running the database.
* Before running and connecting the database, we need to create a database.
### Cloud to Local connection
* In the projects tab (in the left), click "+ New",create a new project and give it a name.
* In the right side, click "+ Add" and in the dropdown select "Local DBMS", give a database name and give a simple password, and click "Create".
```yml
# Details used till now
project_name:
    "NBA"
database_details:
    name:
        "NBA NEO4J"
    password:
        "password"
```
* A new graph database will be created, go ahead and start it. Now, we need to connect to this database to query and CRUD.
* In the left most tab, create "Graph App" and select "Neo4j Brower". It will open up the Neo4j browser. Now, you are successfully connected your local database to browser for querying.

## Querying for Nodes
---
* "MATCH" is the keyword we use when we start querying
* A node in Cipher is already represented in a parenthesis
    ```sql
    MATCH (n)
    RETURN n
    ```
* The above code considers variable "n" to a node in the graph database and returns the same node "n". Since, it is a variable with no conditions, it will return all the nodes and edges connecting these nodes (even though we didn't ask for it, it will still return if the nodes are connected)
* Let's select all the "PLAYER" nodes (player is a label of the node. Means, we are filtering the nodes based on the node labels)
    ```sql
    MATCH (n:PLAYER)
    RETURN n
    ```
* To get the node properties in a table (getting names of the players below, and using "player" as the variable name for the player nodes)
    ```sql
    MATCH (player:PLAYER)
    RETURN player.name
    ```
* Using alias
    ```sql
    MATCH (player:PLAYER)
    RETURN player.name AS name, player.height AS height
    ```

## Filtering for Nodes
---
In the previous section, we learnt how to filter the data based on the node labels. Let's go in more detail and check how to filter the data based on the node properties using "WHERE" statement.
* Let's get "LeBron James" node
    ```sql
    MATCH (player:PLAYER)
    WHERE player.name = "LeBron James"
    RETURN player
    ```
* Casing is important when using the WHERE statement
* Instead of using WHERE statement, we can also use a dictionary as shown below
    ```sql
    MATCH (player:PLAYER {name: "LeBron James"})
    RETURN player
    ```
* We can use multiple conditions in the matching dictionary. Note: it uses AND condition when you are specifying two or more properties
    ```sql
    MATCH (player:PLAYER {name: "LeBron James", height: 2.06})
    RETURN player
    ```
* Let's get all the nodes whose name is not "LeBron James". For using NOT EQUAL condition, we use <>
    ```sql
    MATCH (player:PLAYER)
    WHERE player.name <> "LeBron James"
    RETURN player
    ```
* Similarly, if we want to find all the players whose height is more than 2 meters
    ```sql
    MATCH (player:PLAYER)
    WHERE player.height >= 2
    RETURN player
    ```
* Filtering using Arithmatic: The players heights and weights are present in the node properties. We don't know their BMI, but we know how to calculate BMI using height and weight information, and we want to filter the nodes based on the players' BMI values.
<br>
<code>BMI = weight/(height)^2</code>
<br>
Let's find all the players whose BMI value is above 25
    ```sql
    MATCH (player:PLAYER)
    WHERE (player.weight/(player.height^2)) > 25
    RETURN player
    ```
We are using parenthesis in the WHERE statement to put together the mathematical operations, it doesn't talk about anything like node, edge, or their properties.
* Filtering based on Multiple conditions: 
    * Players with height <= 2 AND weight >= 100. (we already saw how we can do this using conditional dictionary in the above steps)
        ```sql
        MATCH (player:PLAYER)
        WHERE player.height <= 2 AND player.weight >= 100
        RETURN player
        ```
    * Using OR clause
        ```sql
        MATCH (player:PLAYER)
        WHERE player.height <= 2 OR player.weight >= 100
        RETURN player
        ```
    * If we want get the nodes that are not matching the condition. 
        * Instead of "<=" use ">" and instead of ">=" use "<"
        * Use NOT clause
            * If you want to use NOT on the both the conditions, use a parenthesis like below.
                ```sql
                MATCH (player:PLAYER)
                WHERE NOT (player.height <= 2 OR player.weight >= 100)
                RETURN player
                ```
            * If you want to use NOT on only one condition, try something like shown below (without parenthesis or only parenthesis to player.height, so that NOT will only be applicable to player.height)
                ```sql
                MATCH (player:PLAYER)
                WHERE NOT player.height <= 2 OR player.weight >= 100
                RETURN player
                ```
            * It all boils down to how well you use: AND, OR, and NOT clause together as per the requirement.
* LIMIT and SKIP
    * If we don't want our query result to a bunch of nodes that difficult understand, we can limit the nodes that we can see using LIMIT statement.
    ```sql
    MATCH (player:PLAYER)
    WHERE NOT player.height <= 2 OR player.weight >= 100
    RETURN player
    LIMIT 5
    ```
    * This will give the top 5 nodes based on their IDs
    * If we want to see 3 nodes after the first 5 nodes
    ```sql
    MATCH (player:PLAYER)
    WHERE NOT player.height <= 2 OR player.weight >= 100
    RETURN player
    SKIP 5
    LIMIT 3
    ```
* ORDER BY
    * LIMIT uses ID values as default for ordering the nodes
    * We can also specify the node properties to order our nodes
    * Let's order the players based on their heights in decending order
    ```sql
    MATCH (player:PLAYER)
    WHERE NOT player.height <= 2 OR player.weight >= 100
    RETURN player
    ORDER BY player.height DESC
    ```
* Filtering Multiple nodes at a time
    * Let's get player and coach nodes
    ```sql
    MATCH (player:PLAYER), (coach:COACH)
    RETURN player, coach
    ```
    * Additionally, we can use WHERE, LIMIT, ORDER BY, SKIP, AND, OR, NOT and other statements that we learnt in the previous steps for each variable. E.g.:
    ```sql
    MATCH (player:PLAYER), (coach:COACH), (team:TEAM)
    WHERE player.height >= 2.1
    RETURN player, coach, team
    ORDER BY player.height DESC
    SKIP 5
    LIMIT 5
    ```
    * The above query will result in a table with each connection from player to coach to team.

## Querying and Filtering for Edges
---
* Let's get all the players that play for "LA Lakers"
    * We can't find this information of players teams in the node properties.
    * Teams are different nodes and they are connected with the player nodes with a directed relationship called PLAYS_FOR
    ```sql
    MATCH (player:PLAYER) -[:PLAYS_FOR]-> (team:TEAM)
    WHERE team.name = "LA Lakers"
    RETURN player
    ```
* Using Multiple conditions in the WHERE statement. Return players and teams
    ```sql
    MATCH (player:PLAYER) -[:PLAYS_FOR]-> (team:TEAM)
    WHERE team.name = "LA Lakers" OR team.name = "Dallas Mavericks"
    RETURN player, team
    ```
* Using Edge Properties
    * In the graph that we are using, we are also having edge properties, like salary for the PLAYS_FOR relationship.
    * Let's find all the players who gets more than $35m salary
        * For this, we need to specify the relationship variable name
    ```sql
    MATCH (player:PLAYER) -[contract:PLAYS_FOR]-> (team:TEAM)
    WHERE contract.salary > 35000000
    RETURN player
    ```
    * Let's find all the players along with their teams who play for "LA Lakers" or "Dallas Mavericks" whose salary is $35m.
    ```sql
    MATCH (player:PLAYER) -[contract:PLAYS_FOR]-> (team:TEAM)
    WHERE contract.salary > 3500000 AND (team.name = "LA Lakers" OR team.name = "Dallas Mavericks")
    RETURN player, team
    ```
    * Task: Get all the LeBron James' teammates who make more than $4m.
    ```sql
    MATCH (lebron:PLAYER {name: "LeBron James"}) -[:TEAMMATES]-> (teammate:PLAYER)
    MATCH (teammate:PLAYER) - [contract:PLAYS_FOR] -> (team:TEAM)
    WHERE contract.salary >= 40000000
    RETURN teammate
    ```
    The above query is little complex as we are using multiple MATCH statements

## Data Aggregation
---
###  COUNT
Let's consider an example for finding the number of games a particular player has played. To know this, we can using the PLAYED_AGAINST relationship
```sql
MATCH (player:PLAYER) - [games_played:PLAYED_AGAINST] -> (team:TEAM)
RETURN player.name AS name, COUNT(games_played) AS games_played
```

## CRUD
---

## Reference
---
* [Neo4j (Graph Database) Crash Course](https://www.youtube.com/watch?v=8jNPelugC2s)

* Other links:
    * https://github.com/harblaith7/Neo4j-Crash-Course/blob/main/01-initial-data.cypher
    * https://graphdb.ontotext.com/documentation/10.2/
    * https://www.youtube.com/watch?v=hFsXCsZXLho
    * https://www.youtube.com/watch?v=GQtyRmT0DeU
    * https://www.youtube.com/watch?v=A2rXPJk9Y7E

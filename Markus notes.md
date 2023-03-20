# Knowledge Graph concepts from Markus Lecture

## Links

* [Reasonator](https://reasonator.toolforge.org): HTML or GUI version of Wikidata knowledge graph
* [Query Wikidata](https://query.wikidata.org): Interface for Quering Wikidata using SparQL and get results

## Syntax of wikidata queries

**In the below example we are finding the father of Evan Greenberg (The CEO of Chubb), using SqarkQL language and wikidata knowledge graph.**
```sql
SELECT ?father
WHERE {
  wd:Q5415394 wdt:P22 ?father
}
```
* the query format is almost similar to SQL
* wd: is used for subject
* wdt: is used for relationship
* ?variable_name is used to find the unknown object
* ? is followed by the variable name. we just used father as the placeholder, the variable name can be anything.
* the code "Q5415394" represents Evan Greenberg, and "P22" represents father. Got both of them by searching them in [Reasonator](https://reasonator.toolforge.org)
* the output of the above query would be...
> wd:Q1911332
* We have to decode this code to get the answer of the query

**We can also get the result directly in english language using the below syntax**
```sql
SELECT ?father ?fatherLabel
WHERE {
  wd:Q5415394 wdt:P22 ?father
  SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE]".}
}
```
* Notice we are adding two things in the above code compared to the previous one
* 1. In the SELECT statement, we are adding one more variable after our previous variable. We want to get the english version of the output code. Therefore, we are adding the same variable name and "Label" next to it without any spaces, and with capital "L".
* 2. In the WHERE statement, we are adding another line, this line will give the value to our labelled variable in the select statement. 

**Chaining of conditions or statements**
```sql
SELECT ?boardmember ?boardmemberLabel
WHERE 
{
    wd:Q66 wdt:P3320 ?boardmember.
    ?boardmember wdt:P19 wd:Q30.
    SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE]".
    }
}
```
* In the above query, we are finding the board members of Boeing company, whose place of birth is USA.
* The first line in the WHERE statement is about finding the board members of Boeing
* The second line in the WHERE statement is about the finding the board members whose place of birth is USA  
* The dot at the end of every line in the WHERE statement is necessary as it represents the end of one condition in the query, otherwise it will throw an error. As we are chaining the conditions in the query, we without having to write multiple queries based on the previous results.
* The SERVICE statement for getting the labels of the results in the WHERE statement, should be formatted in the same way. Some minor changes may also result in errors.       

**We can query for multiple relationship types**
```sql
SELECT ?boardmember ?boardmemberLabel
WHERE 
{
    wd:Q66 ( wdt:P3320 | wdt:P169 ) ?boardmember.
    SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE]".
    }
}
```
* In the above query, we are looking for Board members or the CEOs of Boeing company.

**Getting the relationship between two nodes/entities**
```sql
SELECT ?rel ?relLabel
WHERE
{
    wd:Q66 ?rel wd:Q201815
    SERVICE wikibase: label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE]"}
}
```
* This code will result in all the relationships between Boeing and McDonnell Douglas

**We can query a complete subgraph of the subject to depth=1**
```sql
SELECT ?relLabel ?xLabel
WHERE
{
    wd:Q66 ?rel ?x.
    SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]".}
}
```
* In the above query, we are finding all the nodes that are related to Boeing, and their relationship
* Since we are also finding the relationship, we have two variable and those two variables are present in one line in WHERE statement.
* This will result in a list of rows, with two columns, one showing the relationship, and the other one showing the entities/nodes connected to Boeing with that relationship.
* The relationships look like wikidata URL (e.g.: http://www.wikidata.org/prop/direct/P1296), we just want the last part of the URL. In python, we can simply extract it and get the label of it.
* The outputs can be in different languages, we can restrict it by changing "[AUTO_LANGAUGE]" to "[@en]"
* We will also get some junk data, that doesn't make any sense. We can remove this data using regular expressions and some other data cleaning techniques.

**We can query a complete subgraph of the subject to depth=2**
```sql
SELECT ?rel1Label ?x1Label ?rel2Label ?x2Label
WHERE
{
    wd:Q66 ?rel1 ?x1.
    ?x1 ?rel2 ?x2.
    SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE]".}
}
```
* Note: we are only finding the labels of the results and not the codes, just to minimize the no. of columns in the output for better understanding of the output.
* This query is the combination of querying a subgraph of depth=1 and chaining
* First we are finding the all the entities and relations that are related to the given node
* Then we are finding the all the nodes that are connected to the nodes that are connected the given node and the relationships between them.
* The above query is given almost 19k outputs
* One of the nodes that is responsible for getting so many results is USA, which is present at depth=1
* If we remove/filter USA node, we can get less no. of results

**Querying a subgraph of the subject at depth=2 with some filterations**
```sql
SELECT ?rel1Label ?x1Label ?rel2Label ?x2Label
WHERE
{
    wd:Q66 ?rel1 ?x1.
    ?x1 ?rel2 ?x2.
    SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE]"}
    FILTER (NOT EXISTS {?x1 wdt:P30 []})
}
```
* Here, we are removing/filtering out node at depth=1 if it is a *continent*.
* After this filteration, we are getting 15k results.

**Backward Querying**

Till now we have seen how to do forward querying (e.g.: Items that are having forward connection with Boeing). Now, let's see how to do backward queries (relationships that are directed towards Boeing).

```sql
SELECT ?xLabel ?relLabel
WHERE
{
    ?x ?rel wd:Q66.
    SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE]"}
}
```
* Here, we are getting the nodes that are related in backward orientation
* We might also find the nodes that are we found in forward querying, this means that those nodes are connected in two directions.

**Filtering using Regular Expressions**
```sql
SELECT ?relLabel ?xLabel
WHERE
{
    wd:Q66 ?rel ?x
    SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]".}
    FILTER ( NOT EXISTS { ?x wdt:P30 [] } ).
    FILTER (!REGEX(STR(?x), "^[A-Za-z] [-.0-9A-Za-z] {1,}$"))
}
```
* As shown, we can have multiple filter statements
* These filter statements must be separated to with full-stops/dots.
* We can use regular expressions in the filter as shown. (Need more explanation on this part)

**SparQL only returns non-null results: OPTIONAL statements**
SparQL queries only return a result if all the queried entities are non-NULL, this is problematic
* Run the query below and see how many rows are returned
```sql
SELECT ?boardmemberLabel ?positionLabel
WHERE
{
    wd:Q66 wdt:P3320 ?boardmember.
    ?boardmember wdt:P39 ?position.
    SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE]".}
}
```
* In the above code, we are checking if who are board members in Boeing, and what are their current positions
* There are around 12 board members, and the above code will only results in 3 records, as wikidata only has information those 3 board members' current positions.
* To look at all the board members, and their current positions if they are available, and null values, if they are not available. We can use OPTIONAL statement, as shown below.
```sql
SELECT ?boardmemberLabel ?positionLabel
WHERE
{
    wd:Q66 wdt:P3320 ?boardmember.
    OPTIONAL{?boardmember wdt:P39 ?position.}
    SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE]".}
}
```
* Same as previous code, enclosing a statement with curly brackets and OPTIONAL statement before it.
* This will display all the names of the board members, and their current positions (if available).

### Machine learning on Graphs

* Once we have a graph representing an entity we can use Machine Learning (ML) to achieve various goals
* Graph Embedding is one of the most important ML operations in graphs
* It learns representations (vectors) for nodes, edges and the whole graph
* These representations can be used in downstream tasks such as classification and clustering
* There is also another application which you rarely see in NLP is Graph Completion, it is equivalent application of Sentence Completion with much more meaning.
* The family of Graph machine learning algorithms are called as self learning algorithms.
  * As these algorithms will self learn to find the missing links or nodes or both, that should be there but are absent.
  * There are numerous applications being developed based on this self learning property of knowledge graphs. It goes beyond the paradigm of supervised and unsupervised machine learning.
* There are many types of graph embedding each with pros & cons:
  * **Random Walk**
  * **node2vec** (extension of Random Walk)
  * **Graph Convolution Networks (GCN)** (inspired by CNN, instead of pixel neighborhood, we are looking for node neighborhood)
  * **TransE/TransR** (Edit distance between graph or nodes)
  * **GraphSAGE** (State of the art algorithm. This is only algorithm among the rest that uses *node properties* and can create node vectors. What is node property? Let's say, if there are datasets attached to nodes, the other algorithms mentioned above cannot use that dataset, only GraphSAGE can use the dataset for the node and can also create node vector.)

### Random Walk

* It's very similar to word embedding in NLP
* We perform many random walks over the graph
* Each walk creates a sequence of nodes and edges
* We treat this sequence as a sentence (it is in GraphSpeak)
* Then we apply a shallow neural network to learn the embedding of these sentences
* As a result, each node will have a **node vector**.

### node2vec

* This is very similar to the random walk approach with the exception that the walks are not completely random.
* That is, during a walk, at each node, we either decide to go to the next node with Breadth-First-Search (BFS) strategy or a Depth-First-Search (DFS) strategy based on a probability (a hyperparameter)
* Rest is similar to random walk, create sentences in GraphSpeak, apply a word vector model/ a shallow neural network and learn the embeddings in these sentences, find teh node vectors.

### Graph Convolution Networks (GCN)

* This method is inspired by CNNs on images.
* Where CNN treats surrounding pixels of a given pixel as neighbors, GCN treat neighbors of a node the same way.
* This will allow the nodes in the graph to have word embeddings with information of nodes present very far.

### TransE/TransR

* These are mainly used for link prediction and graph completion.

### GraphSAGE

* It is the only Graph Embedding algorithm which takes node properties into account during embedding.
* This is a version GCN, but its embeddings are very local. And, it penalizes the nodes that are including the information of the nodes that are far away, it's because of the loss function, and if change the loss function this behaviour will change.
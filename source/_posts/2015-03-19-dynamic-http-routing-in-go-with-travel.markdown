---
layout: post
title: "Dynamic HTTP Routing in Go with Travel"
date: 2015-03-19 08:37:47 -0700
comments: true
categories: golang, programming, http, traversal, development
---

One thing I found interesting while using the [Pyramid web framework](http://www.pylonsproject.org/) was the idea of ["traversal"](http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/traversal.html) request routing. I've implemented an HTTP router in Go that offers similar functionality called [travel](https://github.com/bkeroack/travel).

If you read that traversal link above it may seem complex--it is, sort of--but let me break it down a bit and explain why I think it's cool:

Using travel, your job as the author is to provide the router with a "root tree" object<sup>1</sup>. This is a nested ``map[string]interface{}`` object that represents a tree of routable resources. Travel tokenizes the request URL and does a recursive lookup. If it fails anywhere<sup>2</sup>, travel automatically returns an appropriate error to the client (404, etc). If it succeeds, it calls one of your named handlers according to a "handler map" you provide<sup>3</sup>.

The nice things about this approach (vs. static route patterns) are:

* Routing is dynamic: arbitrarily nested structures only known at runtime can be expressed in the URL and routed appropriately.
* Less boilerplate code for RESTful endpoints: if your handler is called, the resources in question must exist. No need to do full table scans to, eg, check that user_id exists.
* Separation of data concerns: since routing is done with a tree structure, you could conceivable separate the root tree from the data it references (putting the root tree in a fast RAM-backed store for example) and only load data from the database for successful requests.

To demonstrate some of these benefits I've put together a couple of [example applications](https://github.com/bkeroack/travel-examples). The first of which is a nested HTTP key/value store--implemented in ~150 lines of Go--whose datastore backend is a single JSON file. There's a Vagrantfile in the root of the repository which makes it easy to run and test these applications.

JSON Key-Value
--------------

First let's go over functionality of this tool. It supports GET, PUT and DELETE verbs which retrieve, create/modify and remove keys, respectively. It expects JSON in the request body of a PUT request.

When you first start it up the store is empty:
```bash
$ http GET http://192.168.10.10:8000
HTTP/1.1 200 OK
Content-Length: 2
Content-Type: application/json
Date: Fri, 20 Mar 2015 15:34:26 GMT

{}
```

We can create a simple key:
```bash
$ echo '"bar"' |http --body PUT http://192.168.10.10:8000/foo
{
    "success": "value written"
}
$ http --body GET http://192.168.10.10:8000
{
    "foo": "bar"
}
```

Note that we have to wrap our values in double quotes for them to be valid JSON.

We can also create a complex object:
```bash
$ echo '{"phone": "111-222-3333", "age": 32}' |http --body PUT http://192.168.10.10:8000/mary
{
    "success": "value written"
}
$ http --body GET http://192.168.10.10:8000
{
    "foo": "bar",
    "mary": {
        "age": 32,
        "phone": "111-222-3333"
    }
}
```

We can create new nested values:
```bash
$ echo '"123 Main St."' |http --body PUT http://192.168.10.10:8000/mary/address
{
    "success": "value written"
}
$ http --body GET http://192.168.10.10:8000
{
    "foo": "bar",
    "mary": {
        "address": "123 Main St.",
        "age": 32,
        "phone": "111-222-3333"
    }
}
```

We can alter existing nested values:
```bash
$ echo '{"home": "999-999-9999"}' |http --body PUT http://192.168.10.10:8000/mary/phone
{
    "success": "value written"
}
$ http --body GET http://192.168.10.10:8000
{
    "foo": "bar",
    "mary": {
        "address": "123 Main St.",
        "age": 32,
        "phone": {
            "home": "999-999-9999"
        }
    }
}
```

Of course we can access any nested value directly:
```bash
$ http --body GET http://192.168.10.10:8000/mary/phone/home
"999-999-9999"
```

...and we can delete any value directly:
```bash
$ http --body DELETE http://192.168.10.10:8000/mary/phone/home
{
    "success": "value deleted"
}
$ http --body GET http://192.168.10.10:8000
{
    "foo": "bar",
    "mary": {
        "address": "123 Main St.",
        "age": 32,
        "phone": {}
    }
}
```

We *can't* do this:
```bash
$ http --body GET http://192.168.10.10:8000/mary/phone/home
404 Not Found: [mary phone home]
$ echo '"bob"' |http --body PUT http://192.168.10.10:8000/this/path/does/not/exist/yet
404 Not Found: [this path does not exist yet]
```

Looking at the [code](https://github.com/bkeroack/travel-examples/blob/master/json-key-value/main.go):

* Every request is processed by a [single handler](https://github.com/bkeroack/travel-examples/blob/master/json-key-value/main.go#L44-L131)
* Nowhere does it check if a key exists, nor does it recurse through the data structure at all. That is all handled by travel.

It [initializes the travel router](https://github.com/bkeroack/travel-examples/blob/master/json-key-value/main.go#L139-L151) using the options of "strict traversal"--essentially this means that the resulting handler name can either be "" (the empty string) if traversal fully succeeds or the first failed token if it does not fully succeed. It also sets the DefaultHandler to "" (again, the empty string) and sets a maximum subpath (any tokens remaining if traversal does not fully succeed) to one only for PUT requests (that's the only case where we want a successful request--key creation--if that path does not exist yet). Basically we're forcing all requests to either fail or call the default handler ("").

It passes travel a simple function that reads and deserializes the JSON file. Travel calls this at the start of every request. Using the result returned from that function as the root tree, it performs traversal and either calls the appropriate handler if the request succeeds or the error handler if not.

This is of course a toy example. One big issue is that this application is not safe for concurrent requests. Multiple simultaneous requests could overwrite each other's data or potentially corrupt the JSON file. How could we address this?

One way is to use PostgreSQL's JSON storage type instead of a simple file. Our [next example application](https://github.com/bkeroack/travel-examples/tree/master/postgres-key-value) is essentially identical to the one described above except for the functions that deal with root tree retrieval and storage. Everything else works exactly the same, but we make these modifications:

* Instead of a JSON file, we have a table called "root_tree" with three columns: sequential primary key, created timestamp, jsonb tree.
* Rather than mutate a single row in that table on every request, if the request modifies the tree we simply insert a new row. The table serves as a history of all modifications going back in time.
* The function that fetches the root tree at the start of each request does a simple SELECT on the table in descending order by primary key (which is sequential) with LIMIT 1. That way we get the latest root_tree.

There are a few subtleties with PUT and DELETE though. First, you have to keep in mind that the root tree object (and anything associated with it) 

--------

1. Actually you provide a callback function that fetches the root tree object.
2. This isn't strictly true--using traditional traversal semantics the lookup can fail in certain instances but still invoke a handler. The details are not terribly intuitive but can be found in the original documentation.
3. In the Pyramid/Pylons implementation, the author would provide a nested dictionary and would use decorators on "view" (handler) functions/classes to indicate their "name". We obviously cannot do this in Go, so the "handler map" is a map[string]func that provides similar functionality.

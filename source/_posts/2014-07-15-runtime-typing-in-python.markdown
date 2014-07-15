---
layout: post
title: "Runtime Type Checking in Python"
date: 2014-07-15 12:54:28 -0700
comments: true
categories: Python, programming, coding, types
---

In this post I will advocate for a particular style of Python coding which I call "Runtime Type Checking", in order to
help you write code that has clearer intent, fewer implicit assumptions, and--hopefully--fewer bugs.

Just to be clear: Python doesn't need type checking like a statically-typed language. If you are coming to Python from
another language with static typing, _please_ don't try to force those idioms on Python. However I think it's useful to 
deal with types explicitly *when they matter* which, as we will see, is a lot of the time.

## The Problem

In a nutshell: most (or all) of the methods you write have implicit assumptions about the parameters they accept.

For example, function/method parameters by default will happily accept NoneType objects (as they should). However in the vast
majority of cases methods aren't designed to deal with None, resulting in the familiar 
"*TypeError: 'NoneType' object has no attribute [foo]*" exceptions. This is sort of Python's version of a null reference
exception. You could litter your code with if <variable> blocks, but those are ugly. 

Typically people ignore the possibility of None with the rationale that the code will break somewhere anyway
and some exception will be thrown somewhere. However we want to fail as early as possible, and Runtime Type Checking helps
to make sure that parameter assumptions are enforced.

You might have a function or method like the following:

{% include_code Example lang:python rtc_func_ex1.py %}

What implicit assumptions does this function make?

* 'name' exists (is not None) and is a string (or string-like)
* 'categories' exists (is not None) and is an iterable like list or tuple. (You might extend the assumption to say
that the iterable contains objects of type __str__ or even valid categories that exist)
* 'attributes' is also a container type of some sort (in this case we will say that the function expects it to be a 
dict) but may be empty or None.

## A Solution

Let's encode all these assumptions in the preamble to the function (and add a doctring while we're at it):

{% include_code Typed Example lang:python rtc_typing_example.py %}

Notice the following:

* We assert that the mandatory arguments exist (this will catch any arguments that are None). The first assert
guarantees that both arguments are not None and that empty strings/iterables will be caught.
* We assert that they have the interface/methods that we expect (more on that below).
* We allow an optional argument which *can* be None or a dictionary-like object.

Notice in the above example, I did not do either of the following:

``` python
assert isinstance(categories, list)    #BAD
assert isinstance(attributes, dict)    #BAD
```

Why not?

## <a name="assert_behavior"></a> Assert Behavior (or Interface), Not Identity

One of the many beautiful things about Python is that we don't usually need to care what exact class a given object is,
as long as it exposes the methods/behavior (aka interface) that we need. If I wrote the bad example above and a subsequent user of the 
function passed in a duck-typed dict-like object, the function would fail. That would suck and is unnecessarily restrictive.
 
Instead, assert the presence of the methods we require. For most uses, the minimum interface of a dictionary-like object
is the '\_\_getitem\__' and '\_\_setitem\_\_' methods, so we'll make sure they exist and nothing else. Similarly, the minimum interface
of an iterable is the '\_\_iter\_\_' method. We assert the existence of both of those above.

You could create helper functions to make the code a bit more concise:

{% include_code Typed Example 2 lang:python rtc_typing_example2.py %}

You'll notice that in the above I *am* explicitly testing that "name" is of class __str__, contradicting the rule. For the
base types __str__, __int__ and possibly __float__, I don't see a problem with testing the class directly, but there certainly
could be instances where this would be wrong. YMMV.

## Other Solutions
 
Some Pythonistas might point out that optional type checking already exists in Python 3 in the form of [function 
annotations](http://legacy.python.org/dev/peps/pep-3107/). This allows you to specify function parameter types
in function and method definitions. With them you could use a module like [typeannotations](https://github.com/ceronman/typeannotations)
which raises a TypeError exception in the event of a type mismatch.

I have no problem with these solutions, but I like Runtime Type Checking better.

* Explicit asserts are more flexible. We don't just care about class type, we also care about things like "is integer in
valid range", "is string of length N", "is iterable > N items", etc. __All__ these assumptions should be asserted.
* See [Assert Behavior](#assert_behavior) section above. Most of the time we don't want to lock parameters to just one explicit class.
* No need for third party modules.
* Works in Python 2.x
* Explicit asserts double as documentation and make code intent more clear. They are right there underneath the docstring 
and not off in some decorator definition somewhere.

## Too Slow?

I don't think this argument holds much water. If asserts are too slow you are using the wrong language for your
project. That said, you *can* turn asserts into no-ops by passing the [-O flag](http://stackoverflow.com/questions/2830358/what-are-the-implications-of-running-python-with-the-optimize-flag)
to the Python interpreter. I think this defeats the purpose of writing the type checking in the first place, but it's an option.

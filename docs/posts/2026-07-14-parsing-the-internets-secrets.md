---
date: 2026-07-14
tags:
  - machine-learning
  - security
  - from-the-archive
categories:
  - NLP
  - Data
  - Interactive
authors:
  - dylan
slug: parsing-the-internets-secrets
---

# Parsing the Internet's Secrets

!!! note "From the archive (2015) — rebuilding the interactives"
    Originally posted on my old Ghost blog. Re-publishing as part of the relaunch.
    The original interactive D3 widgets are being rebuilt as live **marimo** cells
    — placeholders are marked 🔁 below.

Given the recent [discussion over *bastions of free speech*](http://www.reddit.com/r/announcements/comments/3dautm/content_policy_update_ama_thursday_july_16th_1pm/), I decided I would blog about a former project, the power of anonymity and do a little analysis over the content posted.

> 🔁 *[figure / interactive — rebuild as a marimo cell]*

A few months ago a friend of mine made a site called *dropcan.co* where anyone could post anything. To see posts, one had to create posts themselves and were given only the prompt:

> Description of something you want to get rid of, a memory you would like forget, a bad idea you know will never work, or just simply any rubbish you encounter in life and are just sick off \[sic\]. Let the web take it.

It was a quaint idea, with not many posts- and then [Reddit](http://www.reddit.com/r/humor/comments/2hr8wz/my_friend_made_a_website_where_you_can_throw_away/) got a hold of the site

The massive spike in the above graph shows the brief period Redditors flocked to the site. The volume is not exceptionally impressive- just a few thousand posts over a small period- but enough to bring the service to its knees. My friend called me, and I rewrote the service, removing inefficiencies and making it so that the site could stand against more serious load. However, the Dropcan never really took off again, so we took down the site and [open sourced](https://github.com/mathexl/dropcanco) it awhile back.

At least that was part of the reason. To be truthful, the site made me uncomfortable. There were bigoted remarks and hateful ideas. Even with a basic censorship, terrible things were said. When the volume got lower and I only casually checked the site- sometimes I found myself removing posts from what was ultimately supposed to be a site open to the idea of free speech. I only did this 3 times, but enough to realize free speech can come at the price of hate. Yet, it's important to note only *a handful* of posts were truly offensive. As a rule, we tried to intervene as little as possible.

## The data in general

A good deal of the posts in the Dropcan truly were trash. A fair few posts looked as if their content was simply copy and pasted. For instance, part of a Django forum, the sidebar from [/r/humor](http://www.reddit.com/r/humor) , a random review of headphones and [some homework](http://www.eecs.umich.edu/courses/eecs481/projects/2/Proj2PropTemplate.pdf). In addition there were a ton of [Loreum Ipsums](http://www.lipsum.com/) (It's crazy how far people went out of their way to not post original content), the source-code of the page itself, and a number of XSS and SQL-injection attempts. Before I helped take over the project, I did [a little trolling](https://gist.github.com/dmadisetti/bad2fde7e7d25bda2f04) as well. Here's a little sample of the trash in Dropcan using the unique words in each post:

> 🔁 *[figure / interactive — rebuild as a marimo cell]*

The cluster covers 279 instances of the word `time`, 205 instances of the word `hate`, yet only 151 instances of the word `love` and 198 permutations of the F word (this was from even before we included a minor filter).

Another interesting trash stat:

but for this I suspect someone just connected the Chuck Norris Joke API to the Dropcan.

## Finding the good Content

There was good content within the bin as well. While some of the posts just complained about Justin Bieber or coffee addiction- there were some insightful and interesting stories. Many of these were sad:

> **when I was 16 my family was in severe debt and poverty. We woke up every morning not knowing if we'd have hot water or electricity.**

Others deeply personal:

> **I'm in love with my best friend. He mercilessly teases me for it. He knows I'm in love with him and he instead fell for my childhood bully. I dated him for a month, and broke up with him because of my depression.**

I felt like I was intruding when I first read a few of these- but under protection of anonymity- these are secrets of the nameless.

So how do we extract the meaningful data from this mess? How do we distinguish between a deep personal insight or secret and the spam and hate? Well I found a very quick solution:

\$\$Q_i=\frac{words\_{unique}^2}{words\_{total}}\$\$

Let's call \$Q_i\$ the 'eloquence quotient' per post. If a post has a lot of unique words and is long, then the post should rank highly for *eloquence*. If the post is 'Le Reddit Army' strung together 169,248 times (this was an actual post, no exaggeration), the eloquence of the post is very low. The following interactive text box should demonstrate this concept:

Eloquence Score: ****  

This solution wasn't perfect, but at least it forced posts like "*Le Reddit Army*" to the bottom along with smaller, less interesting quips. Throwing in English recognition removed source-code dumps and some spam, but it still left undesirable posts. I decided if I was going to sift through my data- I was going to do it in a more sophisticated manner.

## Getting smarter with the data

Given that I had **no** idea what I was looking for, I wanted to visualize the data. Visualizing post data is difficult. Beyond a word cluster, it's difficult to truly explore the nature of all the posts. Instead, I described the posts numerically in terms of length, sentiment, subjectivity, word uniqueness and I used an unsupervised clustering algorithm to break the dataset into readable chunks. This let me visualize the post variety:

> 🔁 *[figure / interactive — rebuild as a marimo cell]*

> There are no labels because this is 6D data projected to 3D, but it still gives a general sense of the post relations

I think you can guess what the outlier is.

I went a bit further and automatically broke up the groups into subgroups. I named these groups and the result can be seen below. This wasn't 100% ideal, since the sentiment parsing didn't always work- but it did a pretty sweet job. Click away to open up the post groups, keep in mind many of these are very weird:

The code to generate the clusters and sunburst graphs [can be found here](https://github.com/dmadisetti/kTrees). I won't bore you with the math, except to say it's a result of nested k-means clusters to a particular threshold. In case you wanted to see the data without the unparsables- check this out:

It was an interesting project overall all. I'm not proud of my work towards the site or what it spawned, but I think the nature of the data itself is interesting. In addition to the code, we're [open-sourcing the messages](https://drive.google.com/file/d/0B_S04CrWlh4leEpxT2lKUFZ0elE/view?usp=sharing) to anyone who is interested. I have not since scrubbed the messages, and as such have left the hurt and the hate, but also the heartfelt romance and personal insights from people around the world. Happy trash diving!

------------------------------------------------------------------------

For this project, I did also write a very hacky [twitter bot](https://twitter.com/dropcanco), but it wasn't successful at all (at least not compared to [my only other bot attempt](http://blog.postmodern.technology/machine-learning-instagram-bot/)). In fact I'm pretty sure it ended up following a fair few NSFW twitter handles and other accounts of dubious nature due to the fact the bot primarily used the hashtags `#trash` and `#garbage`. A poor choice of hashtags in retrospect.

# Catmon Image Tagger App

## Introduction
The *Catmon Image Tagger* provides a user interface to help tag a *Catmon* 
image as either 'Boo' or 'Simba'.

If the cat cannot be identified then the image may also be tagged as 'Unclear'.

The app automatically discards images that are too dark to tag.

The app takes the *Catmon* images on google drive as input - starting with 
the most recent - and saves the tagged image to an appropriately named folder
on google drive.

The app is built with python, streamlit, google_api_python_client, PIL and
protobuf.

## Key Project Files
The 'catmon\_img\_tag\_app.py' is the main python application.

## Run The App
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/terrydolan/catmon-img-tag/main/catmon_img_tag_app.py)

## Catmon Image Tagger User Interface
Here is an example of the app's UI:  
<img src="https://raw.githubusercontent.com/terrydolan/catmon-img-tag/main/images/catmon_img_tag_example_2022-08-10_184100.jpg" width="300">

## Related Catmon Projects
1. *Catmon*: a cat flap monitor application that takes a picture when a cat
enters through the cat flap, tweets it on @boosimba and uploads the image
to google drive.
The application has been running since 2015 on a raspberry pi model B rev 2.  
[Catmon repo](https://github.com/terrydolan/catmon)  
2. *Catmon Image Classifier*: an application that processes the new catmon
tweets and classifies the associated image as 'Boo', 'Simba' or 'Unknown'
using a trained MobileNetV2 convolutional neural network (CNN).
The image classification is tweeted as a reply to the *Catmon* tweet.
The MobileNetV2 model applies transfer learning and was trained, validated and
tested  using the tagged catmon images.
MobileNetV2 was selected because it has a small 'footprint', allowing the
application to be deployed on a raspberry pi.  
[Catmon Image Classifier repo](https://github.com/terrydolan/catmon-img-classifier)  
3. *Catmon Last Seen*: an application that shows when Boo or Simba were 
last seen, using the output from *Catmon* and the *Catmon Image Classifier*.  
[Catmon Last Seen repo](https://github.com/terrydolan/catmon-lastseen)  

Terry Dolan  
August 2022
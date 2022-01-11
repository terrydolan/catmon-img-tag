# -*- coding: utf-8 -*-
"""
Catmon Image Web App

The web app provides a UI to classify catmon images
as either Boo or Simba and move to appropriate folder
on google drive.

To run:
    $streamlit run catmon_img_tag_app.py

History
v0.1.0 - Jan 2022, First version
"""

import io
import streamlit as st
import json
import math
import time
from PIL import Image, ImageStat
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

__author__ = "Terry Dolan"
__copyright__ = "Terry Dolan"
__license__ = "MIT"
__email__ = "terry8dolan@gmail.com"
__status__ = "Beta"
__version__ = "0.1.0"
__updated__ = "January 2022"


# configure streamlit page
st.set_page_config(
    page_title=None, page_icon=":cat:", layout="centered", 
    initial_sidebar_state="auto", menu_items={
    'About': "Catmon Image Tagging App"
    }
)

# define the google drive file id of the root 'catmon-pics' folder
CATMON_PICS_FOLDER_ID = st.secrets["CATMON_PICS_FOLDER_ID"]

# define a dict to hold the tag folder ids on my google drive
# the parent of these folders is the root catmon-pics folder
tag_folder_ids_d = {
    # MyDrive:/catmon-pics/boo_images 
    'Boo': st.secrets["BOO_FOLDER_ID"],
    # MyDrive:/catmon-pics/simba_images             
    'Simba': st.secrets["SIMBA_FOLDER_ID"],
    # MyDrive:/catmon-pics/discard_images 
    'Discard': st.secrets["DISCARD_FOLDER_ID"],
    # MyDrive:/catmon-pics/auto_discard_images 
    'Auto-Discard': st.secrets["AUTO_DISCARD_FOLDER_ID"]
    }

# define image brightness threshold
# any images darker than this threshold will be auto discarded
IMAGE_BRIGHTNESS_THRESHOLD = 25

# initialise session stats data
if "stats" not in st.session_state:
    # First run, initialise
    
    # setup session dictionary to hold the image tag totals
    stats_d = {
        'Boo': 0,
        'Simba': 0,
        'Discard': 0,
        'Auto-Discard': 0,
        'Undo': 0
        }
    st.session_state["stats"] = stats_d
    
# initialise session consecutive tagging data
if "consec" not in st.session_state:
    # First run, initialise
    
    # setup session dictionary to hold the consec tag totals
    consec_d = {
        'name': None,
        'tot': 0
        }
    st.session_state["consec"] = consec_d

# initialise session previous tag data
if "previous_tag" not in st.session_state:
    # First run, initialise
    
    # setup session dictionary to store the previous tag
    previous_tag_d = {
        'image_name': None,
        'image_id': None,
        'tag_name': None
        }
    st.session_state["previous_tag"] = previous_tag_d
    
def check_password():
    """Returns True if the user enters the correct catmon_password.

    Ref: https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso
    """
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["CATMON_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input(
            "Password",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        st.text_input(
            "Password",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True
    
@st.experimental_singleton(suppress_st_warning=True)
def gdrive_connect():
    """Connect to google drive service"""
    print("call to gdrive_connect()")
    
    # load json authentication string from environment variable
    # it may contain escape chars so strict set to False
    service_account_info = json.loads(
        st.secrets["GDRIVE_AUTH"], 
        strict=False)    
 
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    creds = service_account.Credentials.from_service_account_info(
        service_account_info, 
        scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return drive_service

def tag_image(image_name, image_id, tag_name):
    """Tag given image with given tag.
    
    Tagging is achieved by moving the given image to the 
    assigned google drive folder for the given tag.
    """
    print(f'\tDEBUG: {image_name} ({image_id}), {tag_name}')
    
    # set current parent folder id
    image_parents = drive_service.files().get(fileId=image_id,
                                     fields='parents').execute()
    curr_parent_folder_id = ",".join(image_parents.get('parents'))
    
    # set new parent folder id
    new_parent_folder_id = tag_folder_ids_d[tag_name]
    
    try:
        # Move the image file to the selected tag folder
        drive_service.files().update(
            fileId=image_id,
            addParents=new_parent_folder_id,
            removeParents=curr_parent_folder_id,
            fields='id, parents').execute()
    except Exception as e:
        st.error(f"Unexpected error encountered: {e}")
        return
        
            
    # update session data
    if tag_name == st.session_state["consec"]["name"]:
        # consecutive tagging continues
        st.session_state["consec"]["tot"] += 1
    else:
        # new tagging starts
        st.session_state["consec"]["name"] = tag_name
        st.session_state["consec"]["tot"] = 1
        
    st.session_state["stats"][tag_name] += 1
    st.session_state["previous_tag"]["image_name"] = image_name
    st.session_state["previous_tag"]["image_id"] = image_id
    st.session_state["previous_tag"]["tag_name"] = tag_name

def undo_tag_image():
    """Undo previous tag of image.
    
    Report progress using given tag_info_placeholder.
    """    
    if st.session_state["previous_tag"]["image_name"] is None:
        st.error("Nothing to undo")
        return
    
    # extract image data for undo from the session state "previous_tag" data
    image_id = st.session_state["previous_tag"]["image_id"]
    tag_name = st.session_state["previous_tag"]["tag_name"]
    curr_parent_folder_id = tag_folder_ids_d[tag_name]
    
    # set new parent folder id (move the image back to the root folder)
    new_parent_folder_id = CATMON_PICS_FOLDER_ID
    
    # Move the image file to the selected tag folder
    drive_service.files().update(
        fileId=image_id,
        addParents=new_parent_folder_id,
        removeParents=curr_parent_folder_id,
        fields='id, parents').execute()
    time.sleep(1)
        
    # update session data
    st.session_state["stats"][tag_name] -= 1
    st.session_state["consec"]["tot"] -= 1
    if st.session_state["consec"]["tot"] == 0:
        st.session_state["consec"]["name"] = "Undo"
        st.session_state["consec"]["tot"] = 1
        
    st.session_state["stats"]["Undo"] += 1
    st.session_state["previous_tag"]["image_name"] = None
    st.session_state["previous_tag"]["image_id"] = None
    st.session_state["previous_tag"]["tag_name"] = None

def download_drive_image(drive_service, file_id):
    """Download image with given file_id using given drive_service"""
    request = drive_service.files().get_media(fileId=file_id)

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        # print("Download %d%%" % int(status.progress() * 100))

    return Image.open(fh)

def get_drive_image(drive_service):
    """Download the next image file in catmon-pics folder.
    
    Return the image_name, image_id and the image object"""
    FILES_PER_PAGE = 1

    # read next image file in root folder
    query = f"'{CATMON_PICS_FOLDER_ID}' in parents and mimeType='image/jpeg'"
    response = drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        pageSize=FILES_PER_PAGE).execute()

    # extract the image data
    file = response.get('files', [])[0]    
    image_name = file.get('name')
    image_id = file.get('id')
    
    # download the image object
    image_obj = download_drive_image(drive_service, image_id)
    
    return image_name, image_id, image_obj

def brightness(image_obj):
    """Calculate the perceived brightness of a given image object.
    
    Ref: https://stackoverflow.com/questions/3490727/what-are-some-methods-to-analyze-image-brightness-using-python
    Ref: http://alienryderflex.com/hsp.html
    
    "The three constants (.299, .587, and .114) represent the different 
    degrees to which each of the primary (RGB) colors affects human 
    perception of the overall brightness of a color."""
    R_CONST = 0.299
    G_CONST = 0.587
    B_CONST = 0.114
    stat = ImageStat.Stat(image_obj)
    r, g, b = stat.mean
    return math.sqrt(R_CONST*(r**2) + G_CONST*(g**2) + B_CONST*(b**2))


if check_password():
    st.title("Catmon Image Tagging App")
    
    # connect to gdrive and get the next image
    drive_service = gdrive_connect()
    
    # define columns for user image tagging
    col1, col2, col3 = st.columns([0.6, 3, 3])
    col4, col5, col6, col7 = st.columns([1, 1, 1, 3])
    
    # get image to tag
    image_not_ready = True
    duplicate = 0
    while image_not_ready:
        with st.spinner('Loading next image to tag...'):
            image_name, image_id, image_obj = get_drive_image(drive_service)
            
            # get another image if duplicate
            if image_id == st.session_state["previous_tag"]["image_id"]:
                duplicate += 1
                print(f"DEBUG: {image_name}, duplicate {duplicate}")
                with col2.empty():
                    st.write(f"Duplicate image found: {image_name}, requesting another ({duplicate})...)")
                    if duplicate < 3:
                        time.sleep(1)
                        st.empty()
                        continue
        
            # auto discard image if too dark
            image_brightness = brightness(image_obj)
            print(f"DEBUG: {image_name}, brightness: {image_brightness}")
            if image_brightness <= IMAGE_BRIGHTNESS_THRESHOLD:
                with col2.empty():
                    st.write(f"Auto-discarding dark image {image_name})")
                    tag_image(image_name, image_id, 'Auto-Discard')
                    time.sleep(1)
                    st.empty()
            else:
                image_not_ready = False
    
    with col1:
        st.button(
            label='Boo', 
            key='btn_boo', 
            help='Press this button to tag the image as Boo',
            on_click=tag_image,
            args=(image_name, image_id, 'Boo')
            )
        
    with col2:
        st.image(image_obj, caption=image_name)
        st.empty()
        
    with col3:
        st.button(
            label='Simba', 
            key='btn_simba', 
            help='Press this button to tag the image as Simba',
            on_click=tag_image,
            args=(image_name, image_id, 'Simba')
            )
        
    with col5:
        st.button(
            label='Discard', 
            key='btn_discard', 
            help='Press this button to discard the image (no clear cat!)',
            on_click=tag_image,
            args=(image_name, image_id, 'Discard')
            )
        
    with col6:
        st.button(
            label='Undo', 
            key='btn_undo', 
            help='Press this button to undo the previous action',
            on_click=undo_tag_image,
            args=()          
            )

    # debug: show consec stats
    # st.write("consec stats")
    # st.write(st.session_state["consec"])
    
    # show tagging stats
    st.subheader("Tag Metrics")
    col7, col8, col9, col10, col11 = st.columns(5)
    delta_calc = lambda tag: st.session_state["consec"]["tot"] \
            if tag == st.session_state["consec"]["name"] else None
    col7.metric("Boo count", st.session_state["stats"]["Boo"], 
                delta=delta_calc("Boo"))
    col8.metric("Simba count", st.session_state["stats"]["Simba"], 
                delta=delta_calc("Simba"))
    col9.metric("Discard count", st.session_state["stats"]["Discard"], 
                delta=delta_calc("Discard"))
    col10.metric("Auto-Discard count", st.session_state["stats"]["Auto-Discard"], 
                delta=delta_calc("Discard"))
    col11.metric("Undo count", st.session_state["stats"]["Undo"], 
                 delta=delta_calc("Undo"))
    
# show guidelines    
    with st.expander("Tagging Guidelines", expanded=True):
        st.markdown("""- Tag as Boo or Simba if the cat is clearly identifiable.
                    It is ok if image is a *little bit* dark.""")
        st.markdown("""- Discard the image if it is unclear e.g. a very dark 
                    image where a cat is not clearly visible; or if there is 
                    a temporary obstruction e.g. a shopping bag!""")
        st.markdown("""- The tagging of the previous image can be undone.
                    You can only go back one step.""")
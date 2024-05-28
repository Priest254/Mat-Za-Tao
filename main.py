from functools import partial
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from kivy.animation import Animation
from openrouteservice import Client
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Rectangle
from kivy.core.window import Window
from numpy import e
from plyer import gps
from plyer.platforms.win import gps
from geopy.geocoders import Nominatim
from kivy.graphics import Color
from fuzzywuzzy import fuzz, process
import logging
from locations import locations
from kivy_garden.mapview import MapMarkerPopup, MapView
from LineMapLayer import LineMapLayer
from openrouteservice import convert
from kivy.clock import Clock
from kivymd.uix.button import MDFloatingActionButton
from kivymd.app import MDApp
from kivy.uix.screenmanager import Screen

# Create a logger named 'mapscreen' and set its level to DEBUG
logger = logging.getLogger('mapscreen')
logger.setLevel(logging.DEBUG)

# Create a file handler to write the logs to a file named 'mapscreen.log'
file_handler = logging.FileHandler('mapscreen.log')
file_handler.setLevel(logging.DEBUG)

# Create a formatter to format the logs with the date, time, level, and message
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add the formatter to the file handler
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

# Use the logger to log messages in your code
logger.debug('Entering MapScreen')
logger.info('Loading data from Excel file')
logger.error(f'Error loading data: {e}')
logger.warning('Zoom level is too high')


class WelcomeScreen(Screen):
    def __init__(self, name=''):
        self.overlay = None
        self.back_button = None
        self.attribution_button = None
        self.about_button = None
        try:
            super().__init__(name=name)
            self.rect = None
            self.bg = None

        except Exception as e:
            print(f"Error initializing WelcomeScreen: {e}")

    def on_enter(self, *args):
        try:
            super(WelcomeScreen, self).on_enter(*args)

            # Create a BoxLayout to hold the Label and Button
            layout = BoxLayout(orientation='vertical')

            # Add a canvas to the layout
            with layout.canvas.before:

                # Load the image
                self.bg = Image(source="1234.jpg").texture
                self.rect = Rectangle(size=Window.size, texture=self.bg)
                Color(0, 1, 1, 0.2)

            # Update the size and position of the image when the window size changes
            Window.bind(size=self.update_rect)

            # Create the welcome Label and add it to the layout
            welcome_label = Label(text='MAT\n za\nCBD', size_hint=(0.3, 0.1), font_size='50sp', bold=True,
                                  color=[0, 0, 0, 1], pos_hint={'x': 0.35})
            layout.add_widget(welcome_label)

            # Create the 'Go to Map' Button and add it to the layout
            go_to_map_button = Button(text='Stage za Mat', size_hint=(.2, 0.01), font_size='27sp',
                                      color=[0, 0, 100, 1],
                                      pos_hint={'x': .28}, background_color=[1, 1, 1, 0.85], bold=True)
            go_to_map_button.bind(on_release=self.go_to_map)
            layout.add_widget(go_to_map_button)

            # Create the 'Go to OpenStreetMap' Button and add it to the layout
            go_to_osm_button = Button(text='OpenStreetMap', size_hint=(.2, 0.01), font_size='27sp',
                                      color=[0, 0, 100, 1], pos_hint={'x': .28},
                                      background_color=[1, 1, 1, 0.85], bold=True)
            go_to_osm_button.bind(on_release=self.go_to_osm)
            layout.add_widget(go_to_osm_button)

            about_button = Button(text='About', size_hint=(.1, .0075), bold=True, color=[1, 1, 0, 0.85],
                                  pos_hint={'left': 1}, background_color=[0, 0, 0, 0.8])
            about_button.bind(on_release=self.show_about)
            layout.add_widget(about_button)
            self.add_widget(layout)

        except Exception as e:
            print(f"Error entering WelcomeScreen: {e}")

    def go_to_map(self, _):
        try:
            self.manager.current = 'map'
            self.clear_widgets()
        except Exception as e:
            print(f"Error going to map: {e}")

    def go_to_osm(self, _):
        try:
            self.manager.current = 'osm'
            self.clear_widgets()
        except Exception as e:
            print(f"Error going to OpenStreetMap: {e}")

    def show_about(self, _):
        try:
            about_text = ("The application uses data from OpenStreetMap contributors, ODbL 1.0."
                          "\nhttps://www.openstreetmap.org/copyright")
            popup = Popup(title='About (Click outside this window to close)',
                          content=Label(text=about_text, bold=True, color=[1, 1, 1, 1], font_size='18sp'),
                          size_hint=(.6, .3), background_color=[0, 0, 150, 0.2])
            popup.background = '1234.jpg'
            popup.title_color = [1, 1, 0, 1]
            popup.title_size = 15
            popup.open()
        except Exception as e:
            print(f"Error opening page: {e}")

    def go_back(self, _):
        self.manager.current = 'welcome'

    def update_rect(self, instance, _):
        try:
            map_screen = self.manager.get_screen('map')
            self.rect.size = instance.size
            self.overlay.size = instance.size
            if hasattr(self.bg, 'size'):
                self.bg.size = instance.size
            map_screen.update_labels()
        except Exception as e:
            print(f"Error updating rectangle: {e}")


class CustomMarker(MapMarkerPopup):
    bus_stage = StringProperty()
    destination = StringProperty()
    location = StringProperty()
    fare = StringProperty()

    def __init__(self, map_screen, size=20, color=(0.5, 0, 1, 1), **kwargs):
        super(CustomMarker, self).__init__(**kwargs)
        self.color = color
        self.size = (size, size)
        self.title = self.bus_stage
        self.map_screen = map_screen  # Store the reference to the MapScreen instance
        self.selected_marker = None
        self.description = f'Destination: {self.destination}\n\nFare: {self.fare}\n\nLocation: {self.location}'

        self.map_screen.update_labels()

    def on_release(self):
        self.map_screen.update_labels()
        content = BoxLayout(orientation='vertical', padding=[0, 0, 0, 0])
        description_label = (Label(text=self.description, color=[1, 1, 1, 1],
                                   font_size='17sp', bold=True, halign='left'))
        content.add_widget(description_label)
        directions_button = Button(text='Route to Stage', size_hint=(1, 0.13), background_color=[0, 0, 0, 1],
                                   color=[1, 1, 0, 1], font_size='19sp', bold=True)
        directions_button.bind(on_release=self.map_screen.get_directions)
        content.add_widget(directions_button)
        close_button = Button(text='Close', size_hint=(1, 0.13), background_color=[0, 0, 0, 1],
                              color=[1, 1, 0, 1], font_size='17sp', bold=True)
        content.add_widget(close_button)

        self.map_screen.selected_marker = self
        popup = Popup(title=self.bus_stage, content=content, size_hint=(0.3, 0.7))
        popup.title_color = [1, 1, 0, 1]
        popup.title_size = '18sp'
        popup.title_align = 'center'
        popup.content_align = 'left'
        popup.content.pos_hint = {'x': .03}
        popup.background_color = [0, 1, 1, 0.7]
        popup.background = '1234.jpg'
        popup.pos_hint = {'x': .01, 'y': 0}

        # Set the background color of the content to semi-transparent
        content.canvas.before.add(Color(rgba=[0, 0, 0, 0]))
        content.canvas.before.add(Rectangle(pos=content.pos, size=content.size))

        close_button.bind(on_release=popup.dismiss)
        directions_button.bind(on_release=popup.dismiss)
        popup.open()
        super(CustomMarker, self).on_release()


class PinMarker(MapMarkerPopup):
    start_location = StringProperty()

    def __init__(self, map_screen, **kwargs):
        super(PinMarker, self).__init__(**kwargs)
        self.map_screen = map_screen
        self.size = (30, 30)  # Size of the pin image
        self.color = [0, 0, 100, 1]
        self.selected_marker = None

    def on_release(self):
        content = BoxLayout(orientation='vertical', padding=[0, 10, 0, 10])
        content.add_widget(Label(text=f'{self.start_location}',
                                 color=[1, 1, 1, 1], font_size='17sp', bold=True))

        # Create a Popup with a semi-transparent background
        popup = Popup(title='Location', content=content, size_hint=(1, 0.15), background='')
        popup.background_color = [0, 0, 0, 0.7]  # Semi-transparent
        popup.pos_hint = {'x': 0, 'y': 0}
        popup.title_size = '18sp'
        popup.title_align = 'center'
        popup.title_color = [1, 1, 0, 1]
        popup.background_color = [0, 1, 1, 0.7]
        popup.background = '1234.jpg'
        popup.open()
        super(PinMarker, self).on_release()


class OpenStreetMapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_label = None
        self.last_marker = None
        self.zoom_out_button = None
        self.zoom_in_button = None
        self.search_button = None
        self.search_input = None
        self.mapview = MapView()
        self.layout = None
        self.markers = []
        self.pin_markers = []
        self.title_label = None
        self.start_labels = []
        self.geolocated_location = None
        gps()

        # Bind the update_labels method to the mapview events
        self.mapview.bind(on_touch_up=self.update_start_labels)
        self.mapview.bind(on_touch_move=self.update_start_labels)
        self.mapview.bind(on_touch_down=self.update_start_labels)
        self.mapview.bind(on_transform=self.update_start_labels)

        self.mapview.bind(on_size=self.update_start_labels)
        Window.bind(on_size=self.update_start_labels)

    def on_enter(self, *args):
        try:
            super(OpenStreetMapScreen, self).on_enter(*args)
            self.layout = FloatLayout()
            self.mapview = MapView(zoom=13, lat=-1.283288, lon=36.824753)  # coordinates for Nairobi

            self.layout.add_widget(self.mapview)
            self.search_input = TextInput(hint_text='Find Location', size_hint=(.25, .05), pos_hint={'x': 0, 'top': 1})
            self.search_button = Button(text='Search', size_hint=(.1, .05), pos_hint={'x': .2, 'top': 1},
                                        background_color=[0, 0, 0, 1], bold=True, font_size='22sp',
                                        color=[20, 100, 0, 1])
            self.search_button.bind(on_release=self.search_location)
            self.zoom_in_button = Button(text='+', size_hint=(.075, .05), pos_hint={'right': 1, 'top': 1},
                                         background_color=[0, 0, 0, 0.8], color=[0, 0, 1, 1], font_size='40sp')
            self.zoom_in_button.bind(on_release=self.zoom_in)
            self.zoom_out_button = Button(text='-', size_hint=(.075, .05), pos_hint={'right': .925, 'top': 1},
                                          background_color=[0, 0, 0, 0.8], color=[0, 0, 1, 1], font_size='40sp')
            self.zoom_out_button.bind(on_release=self.zoom_out)
            # Create the 'Switch to MapScreen' Button and add it to the layout
            switch_button = Button(text='Stage za Mat', size_hint=(.13, .06), pos_hint={'right': 1, 'y': 0.004},
                                   background_color=[0, 0, 0, 1], bold=True, font_size='22sp', color=[20, 100, 0, 1])
            switch_button.bind(on_release=self.switch_screen)
            # Create the Home to WelcomeScreen' Button and add it to the layout
            back_button = Button(text='Home', size_hint=(.07, .055), pos_hint={'left': 1, 'y': 0.008},
                                 background_color=[0, 0, 0, 1], bold=True, color=[1, 1, 0, 0.7], font_size='22sp')
            back_button.bind(on_release=self.go_back)
            button2 = MDFloatingActionButton(icon="crosshairs-gps", pos_hint={'x': .05, 'y': .85})
            button2.bind(on_release=self.search_location)

            self.layout.add_widget(self.search_input)
            self.layout.add_widget(self.search_button)
            self.layout.add_widget(self.zoom_in_button)
            self.layout.add_widget(self.zoom_out_button)
            self.layout.add_widget(switch_button)
            self.layout.add_widget(back_button)
            self.layout.add_widget(button2)

            self.add_widget(self.layout)

        except Exception as e:
            print(f"Error entering OpenStreetMapScreen: {e}")

    def start_gps(self):
        # Configure GPS
        gps.configure(on_location=self.on_location, on_status=self.on_status)
        # Start GPS
        gps.start(minTime=1000, minDistance=0)

    def on_location(self, **kwargs):
        # This method will be called with the current location
        latitude = kwargs.get('lat')
        longitude = kwargs.get('lon')
        # Center the map on the current location and add a marker
        self.mapview.center_on(latitude, longitude)
        self.add_marker_at_location(latitude, longitude)

    def on_status(self, stype, status):
        # Handle GPS status change
        print(f"GPS Status: {stype} - {status}")

    def stop_gps(self):
        gps.stop()

    def search_location(self, _):
        map_screen = self.manager.get_screen('map')
        try:
            # Get the search term from the input field
            search_term = self.search_input.text
            print("search_term")
            # Use the geocoding service to get the location
            geolocator = Nominatim(user_agent="UoNStudentGeocoder")
            location = geolocator.geocode(search_term)
            print("Location")
            if location:
                self.geolocated_location = location
                self.mapview.center_on(location.latitude, location.longitude)
                if self.last_marker:  # If there is a last marker
                    self.mapview.remove_marker(self.last_marker)  # Remove the last marker

                for self.start_label in self.start_labels:
                    self.mapview.remove_widget(self.start_label)
                self.start_labels.clear()

                marker = PinMarker(map_screen, start_location=f'{location}',
                                   lat=location.latitude, lon=location.longitude)
                self.mapview.add_marker(marker)
                self.pin_markers.append(marker)
                self.last_marker = marker

                x, y = self.mapview.get_window_xy_from(location.latitude, location.longitude,
                                                       self.mapview.zoom)

                # Create the label with the correct position
                self.start_label = Label(text=f'{location}', bold=True, color=[1, 0, 0, 1],
                                         size_hint=(None, None), font_size=16, italic=True)
                self.start_label.size = self.start_label.texture_size
                y_offset = 33
                self.start_label.pos = (x, y + y_offset)  # Set the position of the label

                # Add the label to the map view
                self.mapview.add_widget(self.start_label)
                self.start_labels.append(self.start_label)
                self.update_start_labels()

            else:
                not_found_label = Label(text='Location not found', color=[1, 0, 0, 1], size_hint=(.2, .1),
                                        pos_hint={'bottom': 0, 'right': .5}, bold=True)
                self.layout.add_widget(not_found_label)
                Clock.schedule_once(lambda dt: self.layout.remove_widget(not_found_label), 7)
        except GeocoderServiceError:
            error_label = Label(text='Connect to internet', color=[1, 0, 0, 1], size_hint=(.2, .08),
                                pos_hint={'bottom': 0, 'right': .5}, bold=True)
            self.layout.add_widget(error_label)
            Clock.schedule_once(lambda dt: self.layout.remove_widget(error_label), 5)
        except Exception as e:
            print(f"Error: {e}")

    def update_start_labels(self, *args):
        # Remove all existing labels from the map view
        for self.start_label in self.start_labels:
            self.mapview.remove_widget(self.start_label)
        self.start_labels.clear()

        # Create new labels with updated positions
        for marker in self.pin_markers:
            x, y = self.mapview.get_window_xy_from(marker.lat, marker.lon, self.mapview.zoom)
            adjusted_label = Label(text=f'{self.geolocated_location}', bold=True, color=[0, 0, 0, 1],
                                   size_hint=(None, None), font_size=16, italic=True)
            adjusted_label.size = adjusted_label.texture_size
            y_offset = 33
            adjusted_label.pos = (x, y + y_offset)

            # Add the label to the map view
            self.mapview.add_widget(adjusted_label)
            self.start_labels.append(adjusted_label)

            self.mapview.bind(on_touch_up=self.update_start_labels)
            self.mapview.bind(on_touch_move=self.update_start_labels)
            # If the MapView has a zoom event, bind to that as well
            if hasattr(self.mapview, 'on_zoom'):
                self.mapview.bind(on_zoom=self.update_start_labels)

    def zoom_in(self, _):
        self.mapview.zoom += 1
        self.update_start_labels()

    def zoom_out(self, _):
        self.mapview.zoom -= 1
        self.update_start_labels()

    def switch_screen(self, _):
        for marker in self.markers:
            self.mapview.remove_marker(marker)
        self.markers.clear()
        if hasattr(self, 'line_layer'):
            self.mapview.remove_layer(self.line_layer)
            del self.line_layer
        self.manager.current = 'map'

    def go_back(self, _):
        self.manager.current = 'welcome'


def start_gps():
    # Start the GPS
    gps.start()


def on_status(**kwargs):
    # Check the status code and take appropriate actions
    status = kwargs['status']
    if status == gps.GPS_STATUS_ENABLED:
        # GPS is enabled
        print("GPS enabled")
        # (Optional) Start location updates
        gps.start(min_distance=10, min_time=1000)  # Adjust parameters as needed
    elif status == gps.GPS_STATUS_DISABLED:
        # GPS is disabled
        print("GPS disabled")
        # (Optional) Handle disabled GPS (e.g., display message)
    else:
        # Unknown status
        print("Unknown GPS status")


def stop_gps():
    # Start the GPS
    gps.stop()


def geocode(address):
    geolocator = Nominatim(user_agent="MyKivyApp")
    location = geolocator.geocode(address)
    if location is not None:
        return location.latitude, location.longitude
    else:
        print(f"No location found for address: {address}")
        return None, None


class ListScreen(Screen):
    def __init__(self, **kwargs):
        super(ListScreen, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.data = locations
        self.mapview = MapView()
        self.all_data = locations  # Keep a copy of all data
        self.search_data = []
        self.list_labels = []
        self.last_marker = []
        self.markers = []
        self.list_markers = []
        self.last_marker = None
        main_layout = BoxLayout(orientation='vertical')
        top_bar = BoxLayout(size_hint_y=None, height=50)

        # Add the search input widget to the top bar
        self.search_input = TextInput(hint_text='What is your destination/preferred Sacco', size_hint_x=.4,
                                      font_size='17sp', background_color=[1, 1, 1, 0.6], hint_text_color=[0, 0, 0, 1])
        top_bar.add_widget(self.search_input)

        # Add the search button to the top bar
        search_button = Button(text='Search', size_hint_x=.15, bold=True, color=[1, 1, 0, 1])
        search_button.bind(on_release=self.search)
        top_bar.add_widget(search_button)

        reset_button = Button(text='Show All', size_hint_x=.15, bold=True, color=[1, 1, 0, 1])
        reset_button.bind(on_release=self.reset_search)
        top_bar.add_widget(reset_button)

        # Create the fixed "Scroll to Top" button
        scroll_to_top_button = Button(text='Jump to Top', size_hint_x=.15, bold=True, color=[1, 1, 0, 1])
        scroll_to_top_button.bind(on_release=self.scroll_to_top)
        top_bar.add_widget(scroll_to_top_button)

        # Add the close button to the top bar
        close_button = Button(text='Close', size_hint_x=.15, bold=True, color=[1, 1, 0, 1], pos_hint={'right': 1})
        close_button.bind(on_release=self.go_to_map)
        top_bar.add_widget(close_button)

        main_layout.add_widget(top_bar)

        scroll_view = ScrollView(bar_width=20, bar_color=[0, 0, 1, 1])

        box_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        box_layout.bind(minimum_height=box_layout.setter('height'))
        self.box_layout = box_layout

        for index, item in enumerate(self.data, start=1):
            # Concatenate all relevant information into one string
            info = (f"[color=ffff03]{index}. {item['Name']}[/color]"
                    f"[color=111177]{item['Destination']}[/color] "
                    f"[color=ffffff]{item['Fare']}[/color]"
                    f"[color=000017]{item['Location']}[/color]")
            button = Button(text=info, markup=True, font_size='19sp', size_hint_y=None,
                            height=200, valign='top', halign='left', bold=True)
            button.bind(size=lambda instance, value: setattr(instance, 'text_size', value))
            button.bind(on_release=partial(self.on_button_click, name=item['Name']))
            box_layout.add_widget(button)

        scroll_view.add_widget(box_layout)
        main_layout.add_widget(scroll_view)
        self.add_widget(main_layout)

        with self.canvas.before:
            Window.bind(size=self.update_rect)
            self.bg = Image(source='nai2.jpg', keep_ratio=False, allow_stretch=True)
            self.rect = Rectangle(texture=self.bg.texture, size=Window.size)

    def scroll_to_top(self, instance):
        # Scroll to the top of the ScrollView
        self.box_layout.parent.scroll_y = 1

    def search(self, _):
        try:
            search_term = self.search_input.text.lower()

            combined_terms = [search_term] + [
                f"{search_term} sacco", f"{search_term} travels", f"{search_term} shuttle",
                f"{search_term} metro", f"{search_term} limited", f"{search_term} nissan",
                f"{search_term} nissan sacco", f"{search_term} express", f"{search_term} services",
                f"{search_term} prestige", f"{search_term} company", f"{search_term} shuttle company",
                f"{search_term} premium", f"{search_term} shuttle premium", f"{search_term} circular",
                f"{search_term} classic", f"{search_term} classic commuters", f"{search_term} circular eastleigh",
                f"{search_term} trans", f"super {search_term}", f"{search_term} operators",
                f"{search_term}  classic eastleigh", f"{search_term} genesis", f"{search_term} ltd",
                f"{search_term} t ltd", f"{search_term} line", f"{search_term} rd", f"{search_term} road"
            ]

            self.search_data = [item for item in self.all_data if
                                any(fuzz.ratio(term, bus_stage.lower()) > 90 for term in combined_terms for bus_stage in
                                    item["Name"].lower().split(' | ')) or
                                any(fuzz.ratio(term, destination.lower()) > 90 for term in combined_terms for
                                    destination in
                                    item["Destination"].lower().split(', '))
                                ]
            self.box_layout.clear_widgets()

            # Create new buttons based on the filtered data
            for index, item in enumerate(self.search_data, start=1):
                info = (f"[color=ffff00]{index}. {item['Name']}[/color] "
                        f"[color=111177]{item['Destination']}[/color] "
                        f"[color=ffffff]{item['Fare']}[/color]"
                        f"[color=000017]{item['Location']}[/color]")
                button = Button(text=info, markup=True, font_size='19sp', size_hint_y=None,
                                height=200, halign='left', valign='top', bold=True)
                button.bind(size=lambda instance, value: setattr(instance, 'text_size', value))
                button.bind(on_release=partial(self.on_button_click, name=item['Name']))
                self.box_layout.add_widget(button)

        except Exception as e:
            print(f"Error searching stages: {e}")

    def reset_search(self, _):
        self.box_layout.clear_widgets()

        for index, item in enumerate(self.data, start=1):
            info = (f"[color=ffff00]{index}. {item['Name']}[/color] "
                    f"[color=111177]{item['Destination']}[/color] "
                    f"[color=ffffff]{item['Fare']}[/color]"
                    f"[color=000017]{item['Location']}[/color]")
            button = Button(text=info, markup=True, font_size='19sp', size_hint_y=None,
                            height=200, valign='top', halign='left', bold=True)
            button.bind(size=lambda instance, value: setattr(instance, 'text_size', value))
            button.bind(on_release=partial(self.on_button_click, name=item['Name']))
            self.box_layout.add_widget(button)

    def on_button_click(self, instance, name):
        App.get_running_app().root.current = 'map'
        map_screen = self.manager.get_screen('map')
        map_screen.button_term = name  # Set the button term
        map_screen.button_clicked = True  # Indicate that the button was clicked
        Clock.schedule_once(lambda dt: self.add_marker_to_map(name), 0.8)

    def add_marker_to_map(self, name):
        map_screen = self.manager.get_screen('map')
        try:
            location_found = [item for item in self.data if item['Name'] == name]

            for location in location_found:
                marker = CustomMarker(map_screen, bus_stage=location['Name'],
                                      destination=location['Destination'],
                                      location=location['Location'], lat=location['Latitude'],
                                      lon=location['Longitude'])

                map_screen.mapview.add_marker(marker)
                map_screen.markers.append(marker)

                map_screen.update_labels()

                x, y = map_screen.mapview.get_window_xy_from(location["Latitude"], location["Longitude"],
                                                             map_screen.mapview.zoom)

                # Create the label with the correct position
                map_screen.title_label = Label(text=location["Name"], bold=True, color=[0, 0, 0, 1],
                                               size_hint=(None, None), font_size=14, italic=True)
                map_screen.title_label.size = map_screen.title_label.texture_size
                y_offset = 23
                map_screen.title_label.pos = (x, y + y_offset)  # Set the position of the label

                # Add the label to the map view
                map_screen.mapview.add_widget(map_screen.title_label)
                map_screen.list_labels.append(map_screen.title_label)

                map_screen.mapview.bind(on_size=map_screen.update_labels)
                map_screen.mapview.bind(on_zoom=map_screen.update_labels)

        except Exception as e:
            print(f"Error: {e}")

    def go_to_map(self, _):
        # Switch to the map screen
        App.get_running_app().root.current = 'map'

    def update_rect(self, instance, _):
        try:
            self.rect.size = instance.size
            self.bg.size = instance.size
        except Exception as e:
            print(f"Error updating rectangle: {e}")


class MapScreen(Screen):
    def __init__(self, **kwargs):

        """
        :rtype: object
        """
        self.labels_button = None
        self.list_labels = []
        self.title_label = None
        self.route_status = None
        self.start_lat = None
        self.start_lon = None
        self.data = None
        self.all_data = None
        self.markers = []
        self.pin_markers = []

        try:
            super(MapScreen, self).__init__(**kwargs)
            self.mapview = MapView(zoom=17, lat=-1.283288, lon=36.824753)
            self.line = None
            self.zoom = None
            self.button_markers = []
            self.zoom_out_button = None
            self.zoom_in_button = None
            self.search_button = None
            self.search_input = None
            self.walking_button = None
            self.df = None
            self.last_marker = None  # keep track of the last marker
            self.selected_marker = None
            self.show_all_stages_button = None
            self.start_location_input = None
            self.gps.configure(on_location=self.on_location, on_status=on_status)
            self.start_gps()
            self.stop_gps()
            self.add_widget(self.mapview)
            self.add_widget(self.button)

            # Bind the update_labels method to the mapview events
            self.mapview.bind(on_touch_up=self.update_labels)
            self.mapview.bind(on_touch_move=self.update_labels)
            self.mapview.bind(on_touch_down=self.update_labels)
            self.mapview.bind(on_transform=self.update_labels)

            self.mapview.bind(on_size=self.update_labels)
            Window.bind(on_size=self.update_labels)

        except Exception as e:
            print(f"Error initializing MapScreen: {e}")

    def on_enter(self, *args):
        try:
            super(MapScreen, self).on_enter(*args)
            # self.layout = FloatLayout()
            self.mapview = MapView(zoom=16, lat=-1.283288, lon=36.824753)  # coordinates for Nairobi
            self.route_status = 0

            self.add_widget(self.mapview)
            self.search_input = TextInput(hint_text='Enter Sacco(e.g. Super Metro)/Destination(e.g. Ngara)',
                                          size_hint=(.3, .05), pos_hint={'x': 0, 'top': 1})
            self.search_button = Button(text='Search', size_hint=(.1, .05), pos_hint={'x': .3, 'top': 1},
                                        background_color=[0, 0, 0, 1], bold=True, color=[20, 100, 0, 1],
                                        font_size='22sp')
            self.search_button.bind(on_release=self.search_bus_stage)
            self.zoom_in_button = Button(text='+', size_hint=(.075, .05), pos_hint={'right': 1, 'top': 1},
                                         background_color=[0, 0, 0, 0.8], color=[0, 0, 1, 1], font_size='40sp')
            self.zoom_in_button.bind(on_release=self.zoom_in)
            self.zoom_out_button = Button(text='-', size_hint=(.075, .05), pos_hint={'right': .925, 'top': 1},
                                          background_color=[0, 0, 0, 0.8], color=[0, 0, 1, 1], font_size='40sp')
            self.zoom_out_button.bind(on_release=self.zoom_out)
            self.show_all_stages_button = Button(text='Stage za Mat(list)', size_hint=(.14, .06), bold=True,
                                                 pos_hint={'right': 1, 'top': .13}, background_color=[0, 0, 0, 1],
                                                 font_size='22sp', color=[20, 100, 0, 1])
            self.show_all_stages_button.bind(on_release=self.show_all_stages)
            # Create the 'Switch to OpenStreetMap' Button and add it to the layout
            switch_button = Button(text='OpenStreetMap', size_hint=(.13, .06), bold=True, font_size='22sp',
                                   pos_hint={'right': 1, 'y': 0.004}, background_color=[0, 0, 0, 1],
                                   color=[20, 100, 0, 1])
            switch_button.bind(on_release=self.switch_screen)
            # Create the 'Back to WelcomeScreen' Button and add it to the layout
            back_button = Button(text='Home', size_hint=(.07, .055), pos_hint={'x': 0, 'y': 0.008},
                                 background_color=[0, 0, 0, 1], bold=True, color=[1, 1, 0, 1], font_size='22sp')
            back_button.bind(on_release=self.go_back)

            self.add_widget(self.search_input)
            self.add_widget(self.search_button)
            self.add_widget(self.zoom_in_button)
            self.add_widget(self.zoom_out_button)
            self.add_widget(self.show_all_stages_button)
            self.add_widget(back_button)
            self.add_widget(switch_button)

            self.mapview.bind(on_motion=self.update_labels)

        except Exception as e:
            print(f"Error entering MapScreen: {e}")

    def animate_zoom(self, *args):
        # Create an Animation object for zooming from 13 to 17 over 3 to 5 seconds
        anim = Animation(zoom=17, duration=4)  # Adjust duration as needed
        anim.bind(on_progress=self.on_animation_progress)
        anim.start(self.mapview)
        # Start the animation
        anim.start(self.mapview)

    def on_animation_progress(self, animation, widget, progress):
        # Ensure the zoom level is an integer during the animation
        widget.zoom = int(widget.zoom)

    def go_home(self, instance):
        self.manager.current = 'home'

    def draw_route(self, start, end, profile='foot-walking'):
        client = Client(key='5b3ce3597851110001cf62485e5d59f60cd440db9216647cc6588b70')
        try:
            print("Entered draw route")
            # If a (route) already exists, remove it
            if hasattr(self, 'line_layer'):
                self.mapview.remove_layer(self.line_layer)
                print("Existing route removed")

            routes = client.directions(coordinates=[start, end], profile=profile)
            print("Route fetched")
            geometry = convert.decode_polyline(routes['routes'][0]['geometry'])
            print("Geometry ready")
            coordinates = geometry['coordinates']
            coordinates = [(lon, lat) for lat, lon in coordinates]
            print("Coordinates Ready")
            self.line_layer = LineMapLayer(coordinates=coordinates, color=[0, 0, 1, 10])
            print("Line ready")
            self.mapview.add_layer(self.line_layer, mode="scatter")
            # Calculate bounding box of route coordinates
            self.mapview.trigger_update(True)  # Force the mapview to update

            self.walking_button = Button(text='Walking Route', size_hint=(.11, .04), pos_hint={'x': .44, 'y': .02},
                                         bold=True, background_color=[0, 0, 0, 10], color=[0, 20, 50, 1],
                                         font_size='22sp')
            self.walking_button.bind(on_release=self.submit_start_location)
            self.add_widget(self.walking_button)

            self.car_button = Button(text='Driving Route', size_hint=(.11, .04), pos_hint={'x': .56, 'y': .02},
                                     bold=True, background_color=[0, 0, 0, 10], color=[10, 10, 0, 1],
                                     font_size='22sp')
            self.car_button.bind(on_release=self.submit_start_location_car)
            self.add_widget(self.car_button)

        except Exception as e:
            print("Failed")
            self.display_error("Error drawing route: " + str(e))

    def draw_car_route(self, start, end):
        client = Client(key='5b3ce3597851110001cf62485e5d59f60cd440db9216647cc6588b70')
        try:
            print("Entered draw route")
            # If a (route) already exists, remove it
            if hasattr(self, 'line_layer'):
                self.mapview.remove_layer(self.line_layer)
                print("Existing route removed")

            routes = client.directions(coordinates=[start, end])
            print("Route fetched")
            geometry = convert.decode_polyline(routes['routes'][0]['geometry'])
            print("Geometry ready")
            coordinates = geometry['coordinates']
            coordinates = [(lon, lat) for lat, lon in coordinates]
            print("Coordinates Ready")
            self.line_layer = LineMapLayer(coordinates=coordinates, color=[0, 0, 0, 10])
            print("Line ready")
            self.mapview.add_layer(self.line_layer, mode="scatter")
            # Calculate bounding box of route coordinates
            self.mapview.trigger_update(True)  # Force the mapview to update

        except Exception as e:
            print("Failed")
            self.display_error("Error drawing route: " + str(e))

    def get_directions(self, _):
        # This method is called when the 'Get Directions' button is clicked
        content = BoxLayout(orientation='vertical', padding=[10, 10, 10, 10])
        self.start_location_input = TextInput(hint_text='Where are you?', size_hint=(1, 0.15),
                                              pos_hint={'right': 1, 'top': .25}, background_color=[1, 1, 1, 0.8])
        content.add_widget(self.start_location_input)
        start_location = self.start_location_input.text
        submit_button = Button(text='View Route', size_hint=(1, 0.15), pos_hint={'right': 1, 'top': .05},
                               background_color=[0, 0, 0, 0.4], bold=True, color=[1, 1, 0, 1], font_size='18sp')
        # Use a lambda function to pass the parameters to the submit_start_location method
        submit_button.bind(on_release=lambda _: self.submit_start_location(start_location))
        content.add_widget(submit_button)

        # Create a Popup with a semi-transparent background
        popup = Popup(title='Enter Start Location', content=content, size_hint=(.3, 0.3),
                      background='[0, 0, 0, 0]')
        popup.background_color = [0, 0, 0, 0.5]
        popup.title_align = 'center'
        popup.title_color = [1, 1, 0, 1]
        popup.title_size = 17
        popup.pos_hint = {'right': 1, 'top': 0.3}

        # Set the background color of the content to semi-transparent
        content.canvas.before.add(Color(rgba=[0, 0, 0, 0]))
        content.canvas.before.add(Rectangle(pos=content.pos, size=content.size))
        submit_button.bind(on_release=popup.dismiss)
        popup.open()

    def zoom_in(self, _):
        try:
            if self.mapview.zoom < 30:
                self.mapview.zoom += 1
                self.update_labels()
        except Exception as e:
            print(f"Error zooming in: {e}")

    def zoom_out(self, _):
        try:
            if self.mapview.zoom > 1:
                self.mapview.zoom -= 1
                self.update_labels()
        except Exception as e:
            print(f"Error zooming out: {e}")

    def pan_up(self):
        # Increase the latitude to pan up
        new_lat = self.mapview.center[0] + self.get_lat_increment()
        new_lon = self.mapview.center[1]
        self.mapview.center_on(new_lat, new_lon)
        self.update_labels()

    def pan_down(self):
        # Decrease the latitude to pan down
        new_lat = self.mapview.center[0] - self.get_lat_increment()
        new_lon = self.mapview.center[1]
        self.mapview.center_on(new_lat, new_lon)
        self.update_labels()

    def pan_left(self):
        # Decrease the longitude to pan left
        new_lat = self.mapview.center[0]
        new_lon = self.mapview.center[1] - self.get_lon_increment()
        self.mapview.center_on(new_lat, new_lon)
        self.update_labels()

    def pan_right(self):
        # Increase the longitude to pan right
        new_lat = self.mapview.center[0]
        new_lon = self.mapview.center[1] + self.get_lon_increment()
        self.mapview.center_on(new_lat, new_lon)
        self.update_labels()

    def get_lat_increment(self):
        # Calculate the latitude increment based on the current zoom level
        return 0.01 / self.mapview.zoom  # Adjust this value as needed

    def get_lon_increment(self):
        # Calculate the longitude increment based on the current zoom level
        return 0.01 / self.mapview.zoom  # Adjust this value as needed

    def switch_screen(self, _):
        for marker in self.markers:
            self.mapview.remove_marker(marker)
        self.markers.clear()
        if hasattr(self, 'line_layer'):
            self.mapview.remove_layer(self.line_layer)
            del self.line_layer
        self.manager.current = 'osm'

    def go_back(self, _):
        for marker in self.markers:
            self.mapview.remove_marker(marker)
        self.markers.clear()

        if hasattr(self, 'line_layer'):
            self.mapview.remove_layer(self.line_layer)
            del self.line_layer
        self.manager.current = 'welcome'

    def clear_markers(self, _, clear_markers_button=None):
        # Clear all markers
        for marker in self.markers:
            self.mapview.remove_marker(marker)
        self.markers.clear()

        for self.title_label in self.list_labels:
            self.mapview.remove_widget(self.title_label)
        self.list_labels.clear()

        # Clear the line_layer if it exists
        if hasattr(self, 'line_layer'):
            self.mapview.remove_layer(self.line_layer)
            del self.line_layer
            print("Line layer removed")

        if self.title_label:
            self.mapview.remove_widget(self.title_label)

    def update_markers(self):
        map_screen = self.manager.get_screen('map')
        for marker in self.markers:
            self.mapview.remove_marker(marker)
        self.markers.clear()
        for loc in locations:
            try:
                marker = CustomMarker(map_screen, bus_stage=loc['Name'], destination=loc['Destination'],
                                      location=loc['Location'], lat=loc['Latitude'], lon=loc['Longitude'])
                self.mapview.add_marker(marker)
                self.markers.append(marker)
            except Exception as e:
                print(f"Error creating or adding marker for {loc['Name']}: {e}")

    def search_bus_stage(self, _):
        map_screen = self.manager.get_screen('map')
        try:
            self.data = locations
            self.all_data = locations  # Keep a copy of all data

            # Get the search term from the input field
            search_term = self.search_input.text.lower()

            # Remove all existing markers
            for marker in self.markers:
                self.mapview.remove_marker(marker)
            self.markers.clear()

            for self.title_label in self.list_labels:
                self.mapview.remove_widget(self.title_label)
            self.list_labels.clear()

            for marker in self.pin_markers:
                self.mapview.remove_marker(marker)
            self.pin_markers.clear()

            if hasattr(self, 'line_layer'):
                self.mapview.remove_layer(self.line_layer)
                del self.line_layer

            combined_terms = [search_term] + [
                f"{search_term} sacco", f"{search_term} travels", f"{search_term} shuttle",
                f"{search_term} metro", f"{search_term} limited", f"{search_term} nissan",
                f"{search_term} nissan sacco", f"{search_term} express", f"{search_term} services",
                f"{search_term} prestige", f"{search_term} company", f"{search_term} shuttle company",
                f"{search_term} premium", f"{search_term} shuttle premium", f"{search_term} circular",
                f"{search_term} classic", f"{search_term} classic commuters", f"{search_term} circular eastleigh",
                f"{search_term} trans", f"super {search_term}", f"{search_term} operators",
                f"{search_term}  classic eastleigh", f"{search_term} genesis", f"{search_term} ltd",
                f"{search_term} t ltd", f"{search_term} line", f"{search_term} rd", f"{search_term} road"
            ]

            # Search the location in the data using combined terms
            locations_found = [
                item for item in self.data if
                any(fuzz.ratio(term, bus_stage.lower()) > 90 for term in combined_terms for bus_stage in
                    item["Name"].lower().split(' | ')) or
                any(fuzz.ratio(term, destination.lower()) > 90 for term in combined_terms for destination in
                    item["Destination"].lower().split(', '))
            ]

            if locations_found:

                clear_markers_button = Button(text='Clear Search', size_hint=(.1, .06), bold=True,
                                              color=[20, 100, 0, 1],
                                              pos_hint={'right': 1, 'top': .95}, background_color=[0, 0, 0, 1],
                                              font_size='22sp')
                clear_markers_button.bind(on_release=self.clear_markers)
                self.add_widget(clear_markers_button)

                first_location = locations_found[0]
                self.mapview.center_on(first_location["Latitude"], first_location["Longitude"])
                self.mapview.zoom = 17

                for location in locations_found:
                    # Create a marker for each location
                    marker = CustomMarker(map_screen, bus_stage=location["Name"], destination=location["Destination"],
                                          fare=location["Fare"], location=location["Location"],
                                          lat=location["Latitude"], lon=location["Longitude"])
                    self.mapview.add_marker(marker)
                    self.update_labels()
                    self.markers.append(marker)

                    x, y = map_screen.mapview.get_window_xy_from(location["Latitude"], location["Longitude"],
                                                                 map_screen.mapview.zoom)

                    # Create the label with the correct position
                    self.title_label = Label(text=location["Name"], bold=True, color=[0, 0, 0, 1],
                                             size_hint=(None, None), font_size=14, italic=True)
                    self.title_label.size = self.title_label.texture_size
                    y_offset = 23
                    self.title_label.pos = (x, y + y_offset)  # Set the position of the label

                    # Add the label to the map view
                    map_screen.mapview.add_widget(self.title_label)
                    self.list_labels.append(self.title_label)
                    # Bind the update_labels method to the on_size event of the mapview
                    map_screen.mapview.bind(on_size=self.update_labels)

                    zoom_label = Label(text='Zoom in for a better view', color=[0, 0, 1, 1], size_hint=(.2, .1),
                                       pos_hint={'y': 0, 'x': .42}, font_size='16sp')
                    self.add_widget(zoom_label)

            else:
                not_found_label = Label(text='Stage not found', color=[1, 0, 0, 1], size_hint=(.2, .1), bold=True,
                                        pos_hint={'y': 0.05, 'x': .45}, font_size='17sp')
                self.add_widget(not_found_label)
                Clock.schedule_once(lambda dt: self.remove_widget(not_found_label), 5)

        except GeocoderServiceError:
            error_label = Label(text='Connect to internet', color=[1, 0, 0, 1], size_hint=(.2, .08), bold=True,
                                pos_hint={'y': 0.05, 'x': .45}, font_size='17sp')
            self.add_widget(error_label)
            Clock.schedule_once(lambda dt: self.remove_widget(error_label), 5)
        except Exception as e:
            print(f"Error: {e}")

    def update_labels(self, *args):
        # Remove all existing labels from the map view
        for self.title_label in self.list_labels:
            self.mapview.remove_widget(self.title_label)
        self.list_labels.clear()

        for marker in self.markers:
            x, y = self.mapview.get_window_xy_from(marker.lat, marker.lon, self.mapview.zoom)
            title_label = Label(text=marker.bus_stage, bold=True, color=[0, 0, 0, 1],
                                size_hint=(None, None), font_size=14, italic=True)
            title_label.size = title_label.texture_size
            y_offset = 23
            title_label.pos = (x, y + y_offset)

            # Add the label to the map view
            self.mapview.add_widget(title_label)
            # Append the label to the list_labels for tracking
            self.list_labels.append(title_label)

            self.mapview.bind(on_touch_up=self.update_labels)
            self.mapview.bind(on_touch_move=self.update_labels)
            # If the MapView has a zoom event, bind to that as well
            if hasattr(self.mapview, 'on_zoom'):
                self.mapview.bind(on_zoom=self.update_labels)

    def submit_start_location(self, _):
        try:
            start_location = self.start_location_input.text
            print(start_location)

            # Set up the geolocator
            geolocator = Nominatim(user_agent="UoNStudentGeocoder")
            potential_locations = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Archives']

            # Use FuzzyWuzzy to find the closest match to the entered start location
            closest_match, confidence = process.extractOne(start_location, potential_locations)

            # Check if the confidence is above a certain threshold
            if confidence > 80:
                # Use the closest match as the location to geocode
                location = geolocator.geocode(closest_match)
                print(location)

            # Attempt to geocode the start location
            try:
                location = geolocator.geocode(start_location)
            except GeocoderTimedOut:
                location = None

            print(location)

            if location:
                start_lat, start_lon = location.latitude, location.longitude
                map_screen = self.manager.get_screen('map')

                if self.last_marker:  # If there is a last marker
                    self.mapview.remove_marker(self.last_marker)
                if hasattr(self, 'line_layer'):
                    self.mapview.remove_layer(self.line_layer)
                    del self.line_layer

                marker = PinMarker(map_screen, start_location=f'{location}',
                                   lat=location.latitude, lon=location.longitude)
                self.mapview.add_marker(marker)
                self.pin_markers.append(marker)
                self.last_marker = marker

                # Check if the location is within Nairobi city
                if self.is_within_nairobi(start_lat, start_lon):
                    if self.selected_marker is not None:
                        dest_lat, dest_lon = self.selected_marker.lat, self.selected_marker.lon
                        self.draw_route((start_lon, start_lat), (dest_lon, dest_lat))
                    else:
                        print("No destination marker selected.")
                else:
                    print("Start location is not within Nairobi city. Refining search...")
                    # Refine search by adding 'Nairobi' at the end of the search query
                    refined_location = start_location + ", Nairobi"
                    refined_result = geolocator.geocode(refined_location)
                    print(refined_result)
                    if refined_result and self.is_within_nairobi(refined_result.latitude, refined_result.longitude):
                        start_lat, start_lon = refined_result.latitude, refined_result.longitude

                        if self.last_marker:  # If there is a last marker
                            self.mapview.remove_marker(self.last_marker)
                        if hasattr(self, 'line_layer'):
                            self.mapview.remove_layer(self.line_layer)
                            del self.line_layer

                        marker = PinMarker(map_screen, start_location=f'{refined_result}',
                                           lat=start_lat, lon=start_lon)
                        self.mapview.add_marker(marker)
                        self.pin_markers.append(marker)
                        self.last_marker = marker

                        if self.selected_marker is not None:
                            dest_lat, dest_lon = self.selected_marker.lat, self.selected_marker.lon
                            self.draw_route((start_lon, start_lat), (dest_lon, dest_lat))
                        else:
                            print("No destination marker selected.")
                    else:
                        print("Start location not found within Nairobi city.")
                        self.display_error("Start location not found within Nairobi city.")
            else:
                print("Start location not found.")
                self.display_error("Start location not found")

        except GeocoderServiceError:
            self.display_error("Connect to internet")
            logger.error("Geocoder service error occurred. Please check your internet connection.")

        except Exception as e:
            self.display_error("An error occurred while processing your request.")
            logger.exception("Error in submit_start_location: %s", e)

    def submit_start_location_car(self, _):
        try:
            start_location = self.start_location_input.text
            print(start_location)

            # Set up the geolocator
            geolocator = Nominatim(user_agent="UoNStudentGeocoder")

            # Attempt to geocode the start location
            try:
                location = geolocator.geocode(start_location)
            except GeocoderTimedOut:
                location = None

            print(location)

            if location:
                start_lat, start_lon = location.latitude, location.longitude
                map_screen = self.manager.get_screen('map')

                if self.last_marker:  # If there is a last marker
                    self.mapview.remove_marker(self.last_marker)
                if hasattr(self, 'line_layer'):
                    self.mapview.remove_layer(self.line_layer)
                    del self.line_layer

                marker = PinMarker(map_screen, start_location=f'{location}',
                                   lat=location.latitude, lon=location.longitude)
                self.mapview.add_marker(marker)
                self.pin_markers.append(marker)
                self.last_marker = marker

                # Check if the location is within Nairobi city
                if self.is_within_nairobi(start_lat, start_lon):
                    if self.selected_marker is not None:
                        dest_lat, dest_lon = self.selected_marker.lat, self.selected_marker.lon
                        self.draw_car_route((start_lon, start_lat), (dest_lon, dest_lat))
                    else:
                        print("No destination marker selected.")
                else:
                    print("Start location is not within Nairobi city. Refining search...")
                    # Refine search by adding 'Nairobi' at the end of the search query
                    refined_location = start_location + ", Nairobi"
                    refined_result = geolocator.geocode(refined_location)
                    print(refined_result)
                    if refined_result and self.is_within_nairobi(refined_result.latitude, refined_result.longitude):
                        start_lat, start_lon = refined_result.latitude, refined_result.longitude

                        if self.last_marker:  # If there is a last marker
                            self.mapview.remove_marker(self.last_marker)
                        if hasattr(self, 'line_layer'):
                            self.mapview.remove_layer(self.line_layer)
                            del self.line_layer

                        marker = PinMarker(map_screen, start_location=f'{refined_result}',
                                           lat=start_lat, lon=start_lon)
                        self.mapview.add_marker(marker)
                        self.pin_markers.append(marker)
                        self.last_marker = marker

                        if self.selected_marker is not None:
                            dest_lat, dest_lon = self.selected_marker.lat, self.selected_marker.lon
                            self.draw_car_route((start_lon, start_lat), (dest_lon, dest_lat))
                        else:
                            print("No destination marker selected.")
                    else:
                        print("Start location not found within Nairobi city.")
                        self.display_error("Start location not found within Nairobi city.")
            else:
                print("Start location not found.")
                self.display_error("Start location not found")

        except GeocoderServiceError:
            self.display_error("Connect to internet")
            logger.error("Geocoder service error occurred. Please check your internet connection.")

        except Exception as e:
            self.display_error("An error occurred while processing your request.")
            logger.exception("Error in submit_start_location: %s", e)

    def is_within_nairobi(self, latitude, longitude):
        # Define bounding box coordinates for Nairobi city
        nairobi_bbox = [(-1.45, 36.6), (-1.15, 37.1)]

        # Check if the location is within the bounding box
        if (nairobi_bbox[0][0] <= latitude <= nairobi_bbox[1][0] and
                nairobi_bbox[0][1] <= longitude <= nairobi_bbox[1][1]):
            return True
        else:
            return False

    def display_error(self, message):
        error_label = Label(text=message, color=[1, 0, 0, 1], size_hint=(.2, .08), bold=True, font_size='17sp',
                            pos_hint={'y': 0.05, 'x': .45})
        self.add_widget(error_label)
        Clock.schedule_once(lambda dt: self.remove_widget(error_label), 5)

    def show_all_stages(self, _):
        try:
            for marker in self.markers:
                self.mapview.remove_marker(marker)
            self.markers.clear()
            self.manager.current = 'list'

            # Clear the line_layer if it exists
            if hasattr(self, 'line_layer'):
                self.mapview.remove_layer(self.line_layer)
                del self.line_layer
                print("Line layer removed")

        except Exception as e:
            print(f"Error showing all stages: {e}")

    def on_location(self, **kwargs):
        # Extract latitude and longitude from the received data
        try:
            latitude = kwargs['latitude']
            longitude = kwargs['longitude']

            # Now you have the user's current location
            # You can use this value for start_lon in calculate_route
            self.start_lon = longitude  # Assuming start_lon is a class variable
            self.start_lat = latitude

            # (Optional) Update map center to user's location
            # Handle potential missing keys in the data
            self.mapview.center_on(latitude, longitude)
        except KeyError:
            print("Error: Missing key in location data")


class MyApp(MDApp):
    def build(self):
        try:
            sm = ScreenManager()
            sm.add_widget(WelcomeScreen(name='welcome'))

            map_screen = MapScreen(name="map")
            sm.add_widget(map_screen)
            sm.add_widget(OpenStreetMapScreen(name='osm'))
            sm.add_widget(ListScreen(name='list'))

            return sm
        except Exception as e:
            print(f"Error building app: {e}")


if __name__ == '__main__':
    MyApp().run()

from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapTool
from qgis.core import QgsPointXY, QgsGeometry, QgsFeature, QgsVectorLayer, QgsProject
import utm
import json

# doc: https://qgis.org/pyqgis/master/gui/QgsMapTool.html

class PickerTool(QgsMapTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.box_size_km = 10
        self.canvas = canvas
        self.is_pressed = False
        self.square_layer = None
        
        # Check if the CRS is EPSG:4326
        project_crs = QgsProject.instance().crs().authid()
        if project_crs != 'EPSG:4326':
            QMessageBox.warning(None, "CRS Warning", 
                                "The project CRS is not set to EPSG:4326. "
                                "Please set the project CRS to EPSG:4326 before using this tool.")
            self.canvas.unsetMapTool(self)  # Optionally unset the tool to prevent use

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_pressed = not self.is_pressed
        if self.is_pressed:
            self.point = self.toMapCoordinates(event.pos())
            self.print_coordinates()
            self.get_bbox()
            self.update_square()
        else:
            self.print_utm_json()

    def canvasMoveEvent(self, event):
        if self.is_pressed:
            self.point = self.toMapCoordinates(event.pos())
            self.print_coordinates()
            self.get_bbox()
            self.update_square()

    def update_square(self):
        if not self.square_layer:
            # Create a temporary memory layer to store the square
            self.square_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Temporary_Square", "memory")
            QgsProject.instance().addMapLayer(self.square_layer)

            # Set style to green with 30% transparency
            symbol = self.square_layer.renderer().symbol()
            symbol.setColor(Qt.green)
            symbol.setOpacity(0.3)
        else:
            self.square_layer.dataProvider().truncate()

        utm.to_latlon(self.easting_min, self.northing_min, self.zone_number, self.zone_letter)
        p1_y, p1_x = utm.to_latlon(self.easting_min, self.northing_min, self.zone_number, self.zone_letter)        
        p1 = QgsPointXY(p1_x, p1_y)	# bottom left
        p2_y, p2_x = utm.to_latlon(self.easting_max, self.northing_min, self.zone_number, self.zone_letter)
        p2 = QgsPointXY(p2_x, p2_y)	# bottom right
        p3_y, p3_x = utm.to_latlon(self.easting_max, self.northing_max, self.zone_number, self.zone_letter)
        p3 = QgsPointXY(p3_x, p3_y)	# top right
        p4_y, p4_x = utm.to_latlon(self.easting_min, self.northing_max, self.zone_number, self.zone_letter)
        p4 = QgsPointXY(p4_x, p4_y)	# top left
        
        geometry = QgsGeometry.fromPolygonXY([[p1, p2, p3, p4, p1]])
        
        # Create a new feature and set its geometry
        feature = QgsFeature()
        feature.setGeometry(geometry)

        # Add the feature to the layer
        self.square_layer.dataProvider().addFeature(feature)
        self.square_layer.commitChanges()
        self.square_layer.triggerRepaint()
        self.canvas.clearCache()
        self.canvas.refresh()

    def print_coordinates(self):
        print(f"WGS84 coordinates: Latitude: {self.point.y()}, Longitude: {self.point.x()}")
        
    def get_bbox(self):
        easting, northing, self.zone_number, self.zone_letter = utm.from_latlon(self.point.y(), self.point.x())
        # Calculate half the size of the box in meters (5 km in each direction)
        half_size_m = (self.box_size_km * 1000) / 2
        
        # Calculate the coordinates of the bounding box corners, rounded to full meters
        self.easting_min = round(easting - half_size_m)
        self.easting_max = round(easting + half_size_m)
        self.northing_min = round(northing - half_size_m)
        self.northing_max = round(northing + half_size_m)
    
    def print_utm_json(self):
        bounding_box = {
            "bbox": [self.easting_min, self.northing_min, self.easting_max, self.northing_max],
            "zone_number": self.zone_number,
            "zone_letter": self.zone_letter
        }
        
        # Convert to JSON
        bounding_box_json = json.dumps(bounding_box, indent=4)
        print(bounding_box_json)

# Initialize and set the tool
canvas = iface.mapCanvas()
pickertool = PickerTool(canvas)
canvas.setMapTool(pickertool)

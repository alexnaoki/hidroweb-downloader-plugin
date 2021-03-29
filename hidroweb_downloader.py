# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HidrowebDownloader
                                 A QGIS plugin
 Download hydrological data from ANA's API (Hidroweb)
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-03-27
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Alex Naoki Asato Kobayashi
        email                : alexkobayashi10@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from qgis.core import *

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .hidroweb_downloader_dialog import HidrowebDownloaderDialog
import os.path

from shapely.geometry import Point, Polygon, MultiPolygon
import requests, csv, os, datetime, calendar
import xml.etree.ElementTree as ET

class HidrowebDownloader:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'HidrowebDownloader_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Hidroweb Downloader')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('HidrowebDownloader', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/hidroweb_downloader/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Download hydrological data from Hidroweb'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Hidroweb Downloader'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = HidrowebDownloaderDialog()
            self.dlg.download_button.clicked.connect(self.polygon_station)
            self.dlg.inventarioDownload_button.clicked.connect(self.inventario)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            # print('ok')
            print(self.dlg.file_widget.filePath())


    def polygon_station(self):
        error = self.check_errors()
        if error:
            print('Error')
            # sys.exit()
        else:
            layer_input = self.dlg.mapLayer_box.currentLayer()
            print(layer_input)
            feat = layer_input.getFeatures()
            for l in feat:
                feat_geometry = l.geometry()

            if self.dlg.buffer_spinbox.value() == 0:
                pass
            else:
                feat_geometry = self.create_buffer_polygon(feat_geometry=feat_geometry, distance=self.dlg.buffer_spinbox.value(), segments=5)

            with open(self.dlg.inventario_path.filePath(), encoding='utf8') as csvfile:
                total = len(list(csv.DictReader(csvfile)))
                print(total)

            with open(self.dlg.inventario_path.filePath(), encoding='utf8') as csvfile:
                data = csv.DictReader(csvfile)

                i = 0
                for row in data:
                    i += 1
                    # print(row)
                    self.dlg.progressBar.setValue(i/float(total)*100)
                    if feat_geometry.contains(QgsPointXY(float(row['Longitude']), float(row['Latitude']))):
                        print('aqui')
                        print(row['TipoEstacao'])
                        if (self.dlg.rain_checkbox.isChecked()) and (not self.dlg.flow_checkbox.isChecked()) and (int(row['TipoEstacao'])==2):
                            print('rain checkbox')
                            self.point_station(codigo=row['Codigo'],
                                                      tipoEstacao=row['TipoEstacao'],
                                                      lon=row['Longitude'],
                                                      lat=row['Latitude'])
                        elif (self.dlg.flow_checkbox.isChecked()) and (not self.dlg.rain_checkbox.isChecked()) and (int(row['TipoEstacao'])==1):
                            print('flow checkbox')
                            print(row['Codigo'])
                            self.point_station(codigo=row['Codigo'],
                                                      tipoEstacao=row['TipoEstacao'],
                                                      lon=row['Longitude'],
                                                      lat=row['Latitude'])
                        elif (self.dlg.rain_checkbox.isChecked()) and (self.dlg.flow_checkbox.isChecked()):
                            print('both rain and flow checkbox')
                            self.point_station(codigo=row['Codigo'],
                                                      tipoEstacao=row['TipoEstacao'],
                                                      lon=row['Longitude'],
                                                      lat=row['Latitude'])
                        else:
                            print('Nada selecionado')


                # print(self.dlg.inventario_path.filePath()[:-3])
            self.iface.messageBar().pushMessage('Success', 'Programa finalizado!', level=Qgis.Success)

    def point_station(self, codigo, tipoEstacao, lon, lat):
        layers = list(QgsProject.instance().mapLayers().values())
        layers_name = [l.name() for l in layers]

        s = self.download_station(code=codigo,
                          typeData=tipoEstacao,
                          folder_toDownload=f'{self.dlg.data_folder.filePath()}',
                          lon=lon, lat=lat)

        if (not f'{codigo}_{tipoEstacao}' in layers_name) and (s[0]):
            lyr = QgsVectorLayer("point?crs=epsg:4326&field=id:integer", f"{codigo}_{tipoEstacao}", "memory")
            QgsProject.instance().addMapLayer(lyr)

            target_layer = QgsProject.instance().mapLayersByName(f'{codigo}_{tipoEstacao}')
            target_layer[0].startEditing()
            l_d = target_layer[0].dataProvider()

            feat = QgsFeature(target_layer[0].fields())
            feat.setGeometry(QgsPoint(float(lon), float(lat)))

            if int(tipoEstacao)== 1:
                l_d.addAttributes([QgsField('Date', QVariant.Date), QgsField('Consistencia', QVariant.Int), QgsField('Vazao',QVariant.Double)])

                for i, (date, consis, data) in enumerate(zip(s[1], s[2], s[3])):

                    feat.setAttributes([i, date.strftime('%Y-%m-%d'),consis,data])
                    l_d.addFeatures([feat])

            elif int(tipoEstacao) == 2:
                l_d.addAttributes([QgsField('Date', QVariant.Date), QgsField('Consistencia', QVariant.Int), QgsField('Chuva',QVariant.Double)])

                for i, (date, consis, data) in enumerate(zip(s[1], s[2], s[3])):

                    feat.setAttributes([i, date.strftime('%Y-%m-%d'),consis,data])
                    l_d.addFeatures([feat])

            target_layer[0].updateExtents()
            target_layer[0].commitChanges()
        else:
            pass

    def download_station(self, code, typeData, folder_toDownload, lon, lat):
        if int(typeData) == 1:
            typeData = '3'
        else:
            pass
        params = {'codEstacao': f'{int(code):08}', 'dataInicio': '', 'dataFim': '', 'tipoDados': '{}'.format(typeData), 'nivelConsistencia': ''}
        response = requests.get(r'http://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroSerieHistorica', params)
        # response = requests.get(r'http://telemetriaws1.ana.gov.br/ServiceANA.asmx?op=HidroSerieHistorica', params)
        # print(code,response.status_code)

        tree = ET.ElementTree(ET.fromstring(response.content))
        root = tree.getroot()

        list_data = []
        list_consistenciaF = []
        list_month_dates = []
        lon = float(lon)
        lat = float(lat)
        for i in root.iter('SerieHistorica'):
            codigo = i.find("EstacaoCodigo").text
            consistencia = i.find("NivelConsistencia").text
            date = i.find("DataHora").text
            date = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            last_day = calendar.monthrange(date.year, date.month)[1]
            month_dates = [date + datetime.timedelta(days=i) for i in range(last_day)]
            data = []
            list_consistencia = []
            for day in range(last_day):
                if params['tipoDados'] == '3':
                    value = 'Vazao{:02}'.format(day+1)
                    try:
                        data.append(float(i.find(value).text))
                        list_consistencia.append(int(consistencia))
                    except TypeError:
                        data.append(i.find(value).text)
                        list_consistencia.append(int(consistencia))
                    except AttributeError:
                        data.append(None)
                        list_consistencia.append(int(consistencia))
                if params['tipoDados'] == '2':
                    value = 'Chuva{:02}'.format(day+1)
                    try:
                        data.append(float(i.find(value).text))
                        list_consistencia.append(consistencia)
                    except TypeError:
                        data.append(i.find(value).text)
                        list_consistencia.append(consistencia)
                    except AttributeError:
                        data.append(None)
                        list_consistencia.append(consistencia)
            list_data = list_data + data
            list_consistenciaF = list_consistenciaF + list_consistencia
            list_month_dates = list_month_dates + month_dates

        if len(list_data) > 0:
            rows = zip(list_month_dates,[lon for l in range(len(list_month_dates))],[lat for l in range(len(list_month_dates))], list_consistenciaF, list_data)
            with open(os.path.join(folder_toDownload, f'{codigo}_{typeData}.csv'), 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(('Date','Longitude','Latitude', f'Consistencia_{codigo}_{typeData}', f'Data_{codigo}_{typeData}'))
                for row in rows:
                    writer.writerow(row)
            print('CSV gerado')
            return (True, list_month_dates, list_consistenciaF, list_data)
        else:
            print('Dado insuficiente')
            return (False, list_month_dates, list_consistenciaF, list_data)

    def create_buffer_polygon(self, feat_geometry, distance, segments):
        layers = list(QgsProject.instance().mapLayers().values())
        layers_name = [l.name() for l in layers]
        if not 'buffer_polygon' in layers_name:
            lyr = QgsVectorLayer("polygon?crs=epsg:4326&field=id:integer", f"buffer_polygon", "memory")
            QgsProject.instance().addMapLayer(lyr)

            target_layer = QgsProject.instance().mapLayersByName('buffer_polygon')
            target_layer[0].startEditing()
            l_d = target_layer[0].dataProvider()

            # feats = target_layer[0].getFeatures()
            # for feat in feats:
            #     geom = feat.geometry()
            feat = QgsFeature(target_layer[0].fields())


            feat.setGeometry(feat_geometry.buffer(distance, segments))
            l_d.addFeature(feat)
            target_layer[0].updateExtents()
            target_layer[0].commitChanges()

            f = target_layer[0].getFeatures()
            for l in f:
                l_geometry = l.geometry()

            return l_geometry

    def inventario(self):
        api_inventario = 'http://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroInventario'
        params = {'codEstDE':'','codEstATE':'','tpEst':'','nmEst':'','nmRio':'','codSubBacia':'',
                  'codBacia':'','nmMunicipio':'','nmEstado':'','sgResp':'','sgOper':'','telemetrica':''}
        self.dlg.progressBar_inventario.setValue(2)

        response = requests.get(api_inventario, params)
        self.dlg.progressBar_inventario.setValue(10)

        tree = ET.ElementTree(ET.fromstring(response.content))
        root = tree.getroot()

        self.dlg.progressBar_inventario.setValue(15)
        if os.path.isfile(os.path.join(self.dlg.file_widget.filePath(), f'inventario.csv')):
            print('Arquivo inventario já existe')
            self.dlg.progressBar_inventario.setValue(100)
        else:
            with open(os.path.join(self.dlg.file_widget.filePath(), f'inventario.csv'), 'w',newline='') as f:
                writer = csv.writer(f)
                writer.writerow(('Codigo', 'Latitude','Longitude','TipoEstacao'))
                self.dlg.progressBar_inventario.setValue(20)

                # print(len(root.findall('Codigo')))
                total = len(list(root.iter('Table')))
                j = 0
                self.dlg.progressBar_inventario.setValue(25)

                for i in root.iter('Table'):
                    print(i.find('Codigo').text, i.find('Latitude').text, i.find('Longitude').text, i.find('TipoEstacao').text)
                    writer.writerow((i.find('Codigo').text, i.find('Latitude').text, i.find('Longitude').text, i.find('TipoEstacao').text))
                    j+=1
                    # self.dlg.progressBar_inventario.setValue(j/float(total)*100)
                self.dlg.progressBar_inventario.setValue(100)

            print('Arquivo inventario.csv criado')
            self.dlg.inventario_path.setFilePath(os.path.join(self.dlg.file_widget.filePath(), 'inventario.csv'))
            self.iface.messageBar().pushMessage('Success', 'Download do inventario.csv concluído!', level=Qgis.Success)

    def check_errors(self):
        error = False
        print(self.dlg.inventario_path.filePath()[-4:])
        if (self.dlg.inventario_path.filePath() == None) or (self.dlg.inventario_path.filePath()=='') or (not self.dlg.inventario_path.filePath()[-4:]=='.csv'):
            print(self.dlg.inventario_path.filePath())
            self.iface.messageBar().pushMessage("Error", "inventario.csv não encontrado", level=Qgis.Critical, duration=5)
            error = True
        if self.dlg.mapLayer_box.currentLayer() == None:
            self.iface.messageBar().pushMessage("Error", "Shapefile (Polígono) não encontrado", level=Qgis.Critical, duration=5)
            error = True
        if (not self.dlg.mapLayer_box.currentLayer().crs().authid()=='EPSG:4674') and (not self.dlg.mapLayer_box.currentLayer().crs().authid()=='EPSG:4326'):
            print()
            self.iface.messageBar().pushMessage("Error", "Shapefile (Polígono) com Sistema de Coordenadas incorreto. O correto é Sirgas2000 ou WGS84.", level=Qgis.Critical, duration=5)
            error = True
        if (self.dlg.data_folder.filePath() == None) or (self.dlg.data_folder.filePath() == ''):
            self.iface.messageBar().pushMessage("Error", "Nenhuma pasta selecionada para o download", level=Qgis.Critical, duration=5)
            error = True
        return error

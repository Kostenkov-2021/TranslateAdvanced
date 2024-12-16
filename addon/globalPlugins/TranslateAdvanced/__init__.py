# -*- coding: utf-8 -*-
# Copyright (C) 2024 Héctor J. Benítez Corredera <xebolax@gmail.com>
# Este archivo está cubierto por la Licencia Pública General de GNU.
#
# Carga NVDA
import globalPluginHandler
import addonHandler
import languageHandler
import logHandler
import globalVars
import ui
import gui
import api
import speech
import textInfos
from speech import *
from scriptHandler import script, getLastScriptRepeatCount
from nvwave import playWaveFile
# Carga Python
import os
import wx
import time
from threading import Thread
# Carga personal
from .app.managers.managers_settings import GestorSettings
from .app.managers.managers_lang import TraductorIdiomas
from .app.managers.managers_translate import GestorTranslate
from .app.managers.managers_cache import LocalCacheHandler
from .app.managers.managers_clipboard import ClipboardMonitor
from .app.managers.managers_apis import APIManager
from .app.managers.managers_updates_langs import GestorRepositorios
from .app.managers.managers_helps import AdministradorAyuda
from .app.guis.guis_options import ConfigDialog
from .app.guis.guis_lang import DialogoLang
from .app.guis.guis_progress import ProgressDialog
from .app.guis.guis_result import DialogResults
from .app.guis.guis_hostory import DialogHistory
from .app.guis.guis_update import UpdateDialog
from .app.guis.guis_progress_update import ProgresoDescargaInstalacion
from .app.guis.guis_guitrans import TranslateDialog
from .app.utils.utils_security import disableInSecureMode
from .app.utils.utils_network import check_internet_connection, realizar_solicitud_https
from .app.utils.utils_various import getSelectedText
from .app.utils.utils_nvda import mute

# Carga traducción
addonHandler.initTranslation()

@disableInSecureMode
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""
	Clase principal del complemento Traductor Avanzado.
	"""
	def __init__(self, *args, **kwargs):
		"""
		Inicializa el complemento y comienza la verificación de conexión a internet.
		"""
		super(GlobalPlugin, self).__init__(*args, **kwargs)

		# Gestores globales
		self.gestor_settings = None
		self.gestor_lang = None
		self.gestor_translate = None
		self.gestor_portapapeles = None
		self.gestor_apis = None
		self.gestor_repositorio = None
		self.gestor_ayuda = None
		# Utilidades
		self._cache = None
		self.menu = None
		self.oldSpeak = None
		# Bandera para la activación y desactivación de la capa de comandos
		self.switch = False
		# Comprobación de almacén de certificados raíz de Windows.
		# Si no están correctos se actualizan.
		url = "https://www.google.com"
		contenido = realizar_solicitud_https(url)
		if not contenido.get("succesful", True):
			msg = \
_("""Se a encontrado errores en la carga del complemento.

Error:

{}""").format(contenido.get("data"))
			logHandler.log.error(msg)
			self.IS_OK = False
		else:
			self.IS_OK = True

		self.__inicio()

	def __inicio(self):
		"""
		Inicializa los gestores y configura el menú de NVDA.
		"""
		# Carga el gestor de ajustes y todo lo necesario
		self.gestor_settings = GestorSettings(self)
		# Gestor de Ayudas
		self.gestor_ayuda = AdministradorAyuda()
		# Gestor de APIS
		self.gestor_apis = APIManager(self.gestor_settings.file_api)
		# Carga el cache
		self._cache = LocalCacheHandler(self.gestor_settings, logHandler)
		if self.gestor_settings.chkCache:
			self._cache.loadLocalCache()
		# Carga gestor de lenguajes
		self.gestor_lang = TraductorIdiomas(self)
		# Carga el gestor de traducción y todo lo necesario
		self.gestor_translate = GestorTranslate(self)
		self.gestor_settings._nvdaSpeak = speech._manager.speak
		self.gestor_settings._nvdaGetPropertiesSpeech = speech.getPropertiesSpeech
		speech._manager.speak = self.gestor_translate.speak
		speech.getPropertiesSpeech = self.gestor_settings._nvdaGetPropertiesSpeech
		self.oldSpeak = speech.speech.speak
		speech.speech.speak = self.gestor_translate.mySpeak

		self.gestor_settings._enableTranslation = False
		# Gestor del portapapeles
		self.gestor_portapapeles = ClipboardMonitor(self)
		# Gestor del repositorio de Github con los idiomas para actualizar o añadir
		self.gestor_repositorio = GestorRepositorios(self, "hxebolax/TranslateAdvanced", rama='master', local_dir=addonHandler.getCodeAddon().path, json_file=os.path.join(self.gestor_settings.dir_root, "languages.json"))
		# Menú de NVDA
		self.menu = gui.mainFrame.sysTrayIcon.preferencesMenu
		self.WXMenu = wx.Menu()
		self.mainItem = self.menu.AppendSubMenu(self.WXMenu, _("&Traductor Avanzado"), "")
		self.settingsItem = self.WXMenu.Append(1, _("&Configuración de Traductor Avanzado"), "")
		self.updateItem = self.WXMenu.Append(2, _("&Actualizar idiomas del complemento (Sin actualizaciones)"), "")
		self.docuSettingsItem = self.WXMenu.Append(3, _("&Documentación del complemento"), "")
		self.donaSettingsItem = self.WXMenu.Append(4, _("&invítame a un café si te gusta mi trabajo"), "")
		items = [self.settingsItem, self.updateItem, self.docuSettingsItem, self.donaSettingsItem]
		for i in items:
			gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onSettings, i)

		if self.IS_OK:
			msg = \
_("""Traductor Avanzado iniciado correctamente.""")
			logHandler.log.info(msg)
		else:
			msg = \
_("""Traductor Avanzado iniciado con errores.""")
			logHandler.log.info(msg)

		self._update(self.update)

	def terminate(self):
		"""
		Finaliza el complemento y guarda la configuración.
		"""
		if not hasattr(self, 'IS_OK') or not self.IS_OK:
			# No hacer nada si el complemento aún no está completamente inicializado
			return
		try:
			speech._manager.speak = self.gestor_settings._nvdaSpeak
			speech.getPropertiesSpeech = self.gestor_settings._nvdaGetPropertiesSpeech
			speech.speech.speak = self.oldSpeak
			if self.gestor_settings.chkCache:
				self._cache.saveLocalCache()
			self.gestor_settings.guardaConfiguracion()
			self.menu.Remove(self.mainItem)
		except Exception as e:
			pass
		super().terminate()

	def chk_banderas(self, menu=False, toogle=False):
		"""
		Verifica condiciones antes de realizar acciones específicas.

		:param menu: Indica si el menú está abierto.
		:param toogle: Indica si se debe alternar una bandera.
		:return: True si todas las condiciones se cumplen, de lo contrario False.
		"""
		if not check_internet_connection():
			msg = \
_("""No se a encontrado conexión a internet.

Si esta conectado por Wifi puede que NVDA iniciara antes que se conectara.

Si esta conectado por cable compruebe su conexión y asegúrese que todo esta correcto.

Espere unos segundos.""")
			gui.messageBox(msg, _("Información"), wx.ICON_INFORMATION) if menu else ui.message(msg)
			return
		if self.gestor_settings.IS_WinON: 
			msg = \
_("""Ya hay una instancia de Traductor Avanzado abierta.

Ciérrela para realizar esta acción.""")
			gui.messageBox(msg, _("Información"), wx.ICON_INFORMATION) if menu else ui.message(msg)
			return False
		if self.gestor_settings.is_active_translate: 
			msg = \
_("""Tiene una traducción en curso. Espere a que termine.""")
			gui.messageBox(msg, _("Información"), wx.ICON_INFORMATION) if menu else ui.message(msg)
			return False
		if toogle:
			if self.gestor_settings._enableTranslation: 
				msg = \
_("""Tiene la traducción simultanea activada.

Desactívela para realizar esta acción.""")
				gui.messageBox(msg, _("Información"), wx.ICON_INFORMATION) if menu else ui.message(msg)
				return False
		return True

	def getScript(self, gesture):
		"""
		Obtiene el script asociado a un gesto específico.

		Si el interruptor está apagado, devuelve el script del complemento global.
		Si el interruptor está encendido y no se encuentra un script asociado al gesto, cierra la capa de comandos.
		Finalmente, intenta devolver el script asociado al gesto desde el complemento global.

		Args:
			gesture (object): El gesto para el cual se busca el script.

		Returns:
			object: El script asociado al gesto o None si no se encuentra.
		"""
		if not self.switch:
			return globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		script = globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		if not script:
			self.closeCommandsLaier()
			return
		return globalPluginHandler.GlobalPlugin.getScript(self, gesture)

	def closeCommandsLaier(self):
		"""
		Elimina los gestos de la capa de comandos y restaura los propios del complemento.

		Desactiva el interruptor, elimina las asociaciones de gestos y emite un sonido de bip.
		"""
		self.play("close")
		self.switch = False
		self.clearGestureBindings()

	@script(gesture=None, description=_("_Activa la capa de comandos. F1 muestra la lista de atajos de una sola tecla"), category=_("Traductor Avanzado"))
	def script_commandsLaier(self, gesture):
		"""
		Activa la capa de comandos.

		Asocia nuevos gestos a las acciones del script, activa el interruptor y emite un sonido de bip.

		Args:
			gesture (object): El gesto que activa este script.
		"""
		if self.chk_banderas():
			self.play("open")
			self.bindGestures(self.gestor_settings.obtener_diccionario_original())
			self.switch = True

	def script_commandList(self, gesture):
		"""
		Cierra la capa de comandos y muestra la lista de comandos de una sola tecla.

		Desactiva la capa de comandos activa y muestra una lista de comandos disponibles al usuario
		mediante un mensaje navegable.

		Args:
		gesture (object): El gesto que activa este script.
		"""
		self.closeCommandsLaier()
		ui.browseableMessage(self.gestor_settings.obtener_descripciones(), _("Lista de comandos de una sola tecla"))

	def play(self, sound):
		"""
		Reproduce un archivo de sonido específico si se proporciona el nombre del sonido.

		Args:
			sound (str): El nombre del archivo de sonido (sin la extensión) que se va a reproducir.
		"""
		if self.gestor_settings.chkSound: playWaveFile(os.path.join(self.gestor_settings.dir_root, 'app', 'data', 'sounds', '{}.wav'.format(sound)))

	def _update(self, func):
		"""
		Función que ejecuta una función dada cada 30 minutos en un hilo separado.

		:param func: Función a ejecutar.
		"""
		def wrapper():
			# Ejecutar la función por primera vez inmediatamente
			func()
			while True:
				# Esperar 30 minutos (1800 segundos)
				time.sleep(1800)
				# Ejecutar la función
				func()
		Thread(target=wrapper, daemon=True).start()

	def update(self):
		"""
		Actualiza la información sobre nuevas versiones y actualizaciones de los idiomas del complemento.

		La función utiliza el gestor de repositorio para comprobar si hay nuevos idiomas o actualizaciones disponibles.
		Si hay actualizaciones disponibles, se actualiza la etiqueta del menú con el número de actualizaciones.
		Si no hay actualizaciones disponibles, se actualiza la etiqueta del menú indicando que no hay actualizaciones.

		Parámetros:
			No recibe parámetros.

		Devuelve:
			No devuelve ningún valor, pero actualiza el estado del menú correspondiente a las actualizaciones.
		"""
		if check_internet_connection():
			self.update = self.gestor_repositorio.comprobar_nuevos_y_actualizaciones()
			if self.update['success']:
				total = len({**self.update['data']['nuevos'], **self.update['data']['actualizaciones']})
				if total == 1:
					msg = _("&Actualizar idiomas del complemento ({} actualización disponible)").format(total)
				else:
					msg = _("&Actualizar idiomas del complemento ({} actualizaciones disponibles)").format(total)
				self.menu.SetLabel(self.updateItem.GetId(), msg)
			else:
				self.menu.SetLabel(self.updateItem.GetId(), _("&Actualizar idiomas del complemento (Sin actualizaciones)"))

	def onSettings(self, event):
		"""
		Maneja los eventos del menú de configuración.

		:param event: Evento de menú.
		"""
		if event.GetId() == 1: # Configuración
			self.script_onSettings(event.GetId(), True)
		elif event.GetId() == 2: # Actualizaciones
			self.script_onUpdate(event.GetId(), True)
		elif event.GetId() == 3: # Documentación
			wx.LaunchDefaultBrowser(addonHandler.Addon(os.path.join(os.path.dirname(__file__), "..", "..")).getDocFilePath())
		elif event.GetId() == 4: # Donaciones
			wx.LaunchDefaultBrowser("https://paypal.me/hjbcdonaciones?country.x=ES&locale.x=es_ES")

	@script(gesture=None, description=_("Abre la configuración del complemento"), category=_("Traductor Avanzado"))
	def script_onSettings(self, event, menu=False):
		"""
		Abre la configuración del complemento.

		:param event: Evento que desencadena la función.
		:param menu: Indica si el menú está abierto.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(menu, True):
			LaunchThread(self, 1).start()

	@script(gesture=None, description=_("Comprueba si hay actualizaciones de idioma del complemento"), category=_("Traductor Avanzado"))
	def script_onUpdate(self,event, menu=False):
		"""
		Abre la comprobación de actualizaciones de idioma del complemento.

		:param event: Evento que desencadena la función.
		:param menu: Indica si el menú está abierto.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(menu, True):
			LaunchThread(self, 7).start()

	@script(gesture=None, description=_("Cambiar idioma de origen"), category=_("Traductor Avanzado"))
	def script_choice_lang_origen(self, event):
		"""
		Cambia el idioma de origen del traductor.

		:param event: Evento que desencadena la función.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			if self.gestor_settings.choiceOnline == 7: # Solo para Microsoft
				LaunchThread(self, 2).start()
			else:
				ui.message(_("El idioma origen solo puede ser cambiado si tiene seleccionado el traductor de Microsoft."))

	@script(gesture=None, description=_("Cambiar idioma de destino"), category=_("Traductor Avanzado"))
	def script_choice_lang_destino(self, event):
		"""
		Cambia el idioma de destino del traductor.

		:param event: Evento que desencadena la función.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			LaunchThread(self, 3).start()

	@script(gesture=None, description=_("Cambiar el modulo de traducción"), category=_("Traductor Avanzado"))
	def script_choice_translate_change(self, event):
		"""
		Cambia el módulo de traducción.

		:param event: Evento que desencadena la función.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			LaunchThread(self, 4).start()

	@script(gesture=None, description=_("Eliminar todas las traducciones en caché para todas las aplicaciones"), category=_("Traductor Avanzado"))
	def script_flushAllCache(self, event):
		"""
		Elimina todas las traducciones en caché para todas las aplicaciones.

		:param event: Evento que desencadena la función.
		"""
		if self.switch:
			self.closeCommandsLaier()
		else:
			if getLastScriptRepeatCount() == 0:
				ui.message(_("Pulse dos veces para eliminar todas las traducciones en caché de todas las aplicaciones."))
				return
		self.gestor_settings._translationCache = {}
		path = self.gestor_settings.dir_cache
		error = False
		if os.path.isdir(path):
			if not os.listdir(path):
				ui.message(_("No hay cache para borrar."))
				return
			for entry in os.listdir(path):
				try:
					os.unlink(os.path.join(path, entry))
				except Exception:
					logHandler.log.error(_(f"Fallo al eliminar {entry}"))
					error = True
		else:
			ui.message(_("El directorio de la cache no existe."))
			return
		ui.message(_("Se ha eliminado toda la cache.")) if not error else ui.message(_("No se a podido eliminar toda la cache."))

	@script(gesture=None, description=_("Eliminar la caché de traducción para la aplicación enfocada actualmente"), category=_("Traductor Avanzado"))
	def script_flushCurrentAppCache(self, event):
		"""
		Elimina la caché de traducción para la aplicación enfocada actualmente.

		:param event: Evento que desencadena la función.
		"""
		try:
			appName = globalVars.focusObject.appModule.appName
		except:
			ui.message(_("No hay aplicación enfocada."))
			return
		if self.switch:
			self.closeCommandsLaier()
		else:
			if getLastScriptRepeatCount() == 0:
				data = languageHandler.getLanguageDescription(self.gestor_translate.get_choice_lang_destino())
				ui.message(_("Pulse dos veces para eliminar todas las traducciones de {} en lenguaje {}").format(appName, self.gestor_translate.get_choice_lang_destino() if data is None else data))
				return
		self.gestor_settings._translationCache[appName] = {}
		fullPath = os.path.join(self.gestor_settings.dir_cache, "{}_{}.json".format(appName, self.gestor_translate.get_choice_lang_destino()))
		if os.path.exists(fullPath):
			try:
				os.unlink(fullPath)
				ui.message(_("Se ha borrado la cache de la aplicación {} correctamente.").format(appName))
			except Exception as e:
				logHandler.log.error(_("Fallo al borrar la cache de la aplicación {} : {}").format(appName, str(e)))
				ui.message(_("Error al borrar la caché de traducción de la aplicación."))
		else:
			ui.message(_("No hay traducciones guardadas para {}").format(appName))

	@script(gesture=None, description=_("Activa o desactiva la cache de traducción"), category=_("Traductor Avanzado"))
	def script_toggleCache(self, event):
		"""
		Activa o desactiva la caché de traducción según el estado actual.
		
		:param event: El evento que desencadena la función.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			# Guarda el estado actual de la traducción
			temp = self.gestor_settings._enableTranslation
			
			# Si la traducción está habilitada, la deshabilita y guarda la caché local si corresponde
			if self.gestor_settings._enableTranslation:
				self.gestor_settings._enableTranslation = False
				temp = True
				if self.gestor_settings.chkCache:
					self._cache.saveLocalCache()
			else:
				temp = False
			
			# Cambia el estado de la caché
			self.gestor_settings.chkCache = not self.gestor_settings.chkCache
			
			# Muestra el mensaje correspondiente a la acción realizada
			if self.gestor_settings.chkCache:
				ui.message(_("Cache de traducción activada."))
			else:
				ui.message(_("Cache de traducción desactivada."))
			
			# Actualiza la configuración de la caché
			self.gestor_settings.setConfig("chkCache", self.gestor_settings.chkCache)
			
			# Si la traducción estaba habilitada, la re-habilita y carga la caché local si corresponde
			if temp:
				self.gestor_settings._enableTranslation = True
				if self.gestor_settings.chkCache:
					self._cache.loadLocalCache()

	@script(gesture=None, description=_("Copiar el ultimo texto traducido al portapapeles"), category=_("Traductor Avanzado"))
	def script_copyLastTranslation(self, event):
		"""
		Copia el último texto traducido al portapapeles si no hay una traducción en curso.
		
		:param event: El evento que desencadena la función.
		"""
		
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			# Verifica si existe texto traducido y si su longitud es mayor a cero
			if self.gestor_settings._lastTranslatedText and len(self.gestor_settings._lastTranslatedText) > 0:
				# Copia el texto traducido al portapapeles
				self.gestor_portapapeles.set_clipboard_text(self.gestor_settings._lastTranslatedText)
				# Muestra un mensaje indicando el texto copiado
				ui.message(_("Se ha copiado lo siguiente al portapapeles: {}").format(self.gestor_settings._lastTranslatedText))
			else:
				# Muestra un mensaje indicando que no hay texto para copiar
				ui.message(_("No se ha podido copiar nada al portapapeles"))

	@script(gesture=None, description=_("Traduce el contenido del portapapeles"), category=_("Traductor Avanzado"))
	def script_ClipboardTranslation(self, event):
		"""
		Traduce el contenido del portapapeles
		
		:param event: El evento que desencadena la función.
		"""
		
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			texto = self.gestor_portapapeles.get_clipboard_text()
			# Verificar si el texto no es None, no está vacío y contiene al menos un carácter alfanumérico
			if texto is not None and texto and any(c.isalnum() for c in texto):
				# Verificar que el texto tenga menos de 3000 caracteres
				if len(texto) < 3000:
					temp = self.gestor_settings._enableTranslation
					self.gestor_settings._enableTranslation = False
					result = self.gestor_translate.translate_various(texto)
					ui.message(result)
					self.gestor_settings._enableTranslation = temp
				else: # Más de 3000 caracteres
					self.gestor_settings._enableTranslation = False
					self.gestor_settings.is_active_translate = True
					LaunchThread(self, 5, texto).start()
			else:
				# Muestra un mensaje indicando que no hay texto para traducir
				ui.message(_("No hay nada para traducir en el portapapeles"))

	@script(gesture=None, description=_("Traduce el último texto verbalizado"), category=_("Traductor Avanzado"))
	def script_speackLastTranslation(self, event):
		"""
		Traduce el último texto verbalizado si no hay una traducción en curso.
		
		:param event: El evento que desencadena la función.
		"""
		
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			texto = self.gestor_settings.ultimo_texto
			# Verificar si el texto no es None, no está vacío y contiene al menos un carácter alfanumérico
			if texto is not None and texto and any(c.isalnum() for c in texto):
				# Verificar que el texto tenga menos de 3000 caracteres
				if len(texto) < 3000:
					temp = self.gestor_settings._enableTranslation
					self.gestor_settings._enableTranslation = False
					result = self.gestor_translate.translate_various(texto)
					ui.message(result)
					self.gestor_settings._enableTranslation = temp
				else: # Más de 3000 caracteres
					self.gestor_settings._enableTranslation = False
					self.gestor_settings.is_active_translate = True
					LaunchThread(self, 5, texto).start()
			else:
				# Muestra un mensaje indicando que no hay texto para traducir
				ui.message(_("No hay nada para traducir"))

	@script(gesture=None, description=_("Activa o desactiva la traducción simultánea Online"), category=_("Traductor Avanzado"))
	def script_toggleTranslateOnline(self, event):
		"""
		Activa o desactiva la traducción simultánea Online.

		Verifica las condiciones necesarias antes de activar o desactivar la traducción Online,
		y muestra mensajes adecuados según el estado actual del sistema.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas():
			if self.gestor_settings._enableTranslation:
				self.gestor_settings._enableTranslation = False
				ui.message(_("Traducción desactivada."))
			else:
				ui.message(_("Traducción activada."))
				self.gestor_settings._enableTranslation = True
			if self.gestor_settings.chkCache:
				self._cache.loadLocalCache() if self.gestor_settings._enableTranslation else self._cache.saveLocalCache()

	@script(gesture=None, description=_("Traduce el texto seleccionado"), category=_("Traductor Avanzado"))
	def script_translate_select(self, event):
		"""
		Traduce el texto seleccionado.

		:param event: Evento que desencadena la función.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			# Obtiene el texto seleccionado
			temp = getSelectedText(api.getCaretObject())
			if not temp['success'] or temp['data'] == '':
				ui.message(_("Sin selección para traducir"))
				return
			# Deshabilita la traducción y activa el estado de traducción
			self.gestor_settings._enableTranslation = False
			self.gestor_settings.is_active_translate = True
			LaunchThread(self, 5, temp['data']).start()

	@script(gesture=None, description=_("Muestra el historial de traducción"), category=_("Traductor Avanzado"))
	def script_translate_history(self, event):
		"""
		Muestra el historial de traducción.

		:param event: Evento que desencadena la función.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			if not self.gestor_settings.historialOrigen:
				ui.message(_("No hay nada en el historial todavía."))
				return
			LaunchThread(self, 6).start()

	@script(gesture=None, description=_("Detecta el idioma seleccionado"), category=_("Traductor Avanzado"))
	def script_detectLang(self, event):
		"""
		Detecta el idioma del texto seleccionado en respuesta a un evento.

		Parámetros:
			event: El evento que dispara la detección de idioma.

		Acciones:
			1. Si el interruptor está activado, cierra la capa de comandos.
			2. Verifica si las banderas están configuradas correctamente.
			3. Obtiene el texto seleccionado utilizando la posición actual del cursor.
			4. Si no hay texto seleccionado, muestra un mensaje de error y termina la ejecución.
			5. Desactiva la traducción y activa el estado de traducción.
			6. Inicia un nuevo hilo para procesar la detección de idioma del texto seleccionado.

		Resultado:
			Procesa la detección del idioma del texto seleccionado y maneja los estados de traducción correspondientes.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			# Obtiene el texto seleccionado
			temp = getSelectedText(api.getCaretObject())
			if not temp['success'] or temp['data'] == '':
				ui.message(_("Sin selección para obtener el idioma"))
				return
			# Deshabilita la traducción y activa el estado de traducción
			self.gestor_settings._enableTranslation = False
			self.gestor_settings.is_active_translate = True
			LaunchThread(self, 8, temp['data']).start()

	@script(gesture=None, description=_("Activar o desactivar el intercambio automático si el origen detectado coincide con el destino (experimental)"), category=_("Traductor Avanzado"))
	def script_toggleLangDetect(self, event):
		"""
		Activa o desactiva el intercambio automático si el origen detectado coincide con el destino.
		
		:param event: El evento que desencadena la función.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			# Cambia el estado de la estado
			self.gestor_settings.chkAltLang = not self.gestor_settings.chkAltLang
			
			# Muestra el mensaje correspondiente a la acción realizada
			if self.gestor_settings.chkAltLang:
				ui.message(_("El intercambio automático está activado. El sistema cambiará automáticamente si el origen detectado coincide con el destino (experimental)."))
			else:
				ui.message(_("El intercambio automático está desactivado. El sistema no realizará cambios automáticos aunque el origen detectado coincida con el destino (experimental)."))

	@script(gesture=None, description=_("Intercambia el idioma principal con el idioma alternativo."), category=_("Traductor Avanzado"))
	def script_toggleLangSwitch(self, event):
		"""
		Intercambia el idioma principal con el idioma alternativo.
		
		:param event: El evento que desencadena la función.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			if self.gestor_settings.chkAltLang:
				# Intercambia los valores entre las dos variables
				self.gestor_settings.choiceLangDestino_google_def, self.gestor_settings.choiceLangDestino_google_alt = (
					self.gestor_settings.choiceLangDestino_google_alt,
					self.gestor_settings.choiceLangDestino_google_def
				)
				
				# Muestra el mensaje correspondiente al cambio realizado
				idiomas_name = self.gestor_translate.data_google.get_values()
				data_def = languageHandler.getLanguageDescription(self.gestor_settings.choiceLangDestino_google_def)
				data_alt = languageHandler.getLanguageDescription(self.gestor_settings.choiceLangDestino_google_alt)
				if data_def is None:
					idioma_def = idiomas_name[self.gestor_translate.data_google.get_index_by_key_or_value(self.gestor_settings.choiceLangDestino_google_def)]
				else:
										idioma_def = data_def
				if data_alt is None:
					idioma_alt = idiomas_name[self.gestor_translate.data_google.get_index_by_key_or_value(self.gestor_settings.choiceLangDestino_google_alt)]
				else:
										idioma_alt = data_alt
				msg = \
_("""El idioma principal y el idioma alternativo han sido intercambiados.

Idioma principal: {}.

Idioma alternativo: {}.""").format(idioma_def, idioma_alt)
				ui.message(msg)
			else:
				ui.message(_("No tiene activado el intercambio automático si el origen detectado coincide con el destino"))

	@script(gesture=None, description=_("Traduce texto del objeto del navegador"), category=_("Traductor Avanzado"))
	def script_obj_translate(self, event):
		"""
		Traduce el texto del objeto seleccionado en el navegador.

		Este script se activa cuando se ejecuta un evento específico y realiza las siguientes acciones:
		1. Si la opción de switch está activada, cierra la capa de comandos.
		2. Verifica las banderas necesarias antes de proceder.
		3. Obtiene el objeto actualmente seleccionado en el navegador.
		4. Intenta extraer el nombre del objeto o su contenido de texto.
		5. Si no se encuentra texto, muestra un mensaje de error y finaliza.
		6. Deshabilita la traducción y activa el estado de traducción en la configuración del gestor.
		7. Verifica si el texto tiene menos de 3000 caracteres.
			- Si es así, traduce el texto y muestra el resultado.
			- Si no, inicia un hilo de traducción para manejar textos más largos.

		:param event: El evento que activa este script.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			# Obtiene el objeto seleccionado
			obj = api.getNavigatorObject()
			texto = obj.name
			if not texto:
				try:
					texto = obj.makeTextInfo(textInfos.POSITION_ALL).clipboardText
					if not texto:
						raise RuntimeError()
				except (RuntimeError, NotImplementedError):
					ui.message(_("El objeto no tiene texto para traducir"))
					return

			# Deshabilita la traducción y activa el estado de traducción
			self.gestor_settings._enableTranslation = False
			self.gestor_settings.is_active_translate = True
			# Verificar que el texto tenga menos de 3000 caracteres
			if len(texto) < 3000:
				result = self.gestor_translate.translate_various(texto)
				ui.message(result)
				self.gestor_settings.is_active_translate = False
			else: # Más de 3000 caracteres
				self.gestor_settings.is_active_translate = True
				LaunchThread(self, 5, texto).start()

	@script(gesture=None, description=_("Interfaz de traducción"), category=_("Traductor Avanzado"))
	def script_gui_translate(self, event):
		"""
		Abre la interfaz de usuario de traducción del complemento.

		Si no hay texto seleccionado, abre la interfaz de traducción en blanco.
		Si hay texto seleccionado, pre-llena la interfaz con el texto seleccionado.

		:param event: Evento que desencadena la función.
		"""
		if self.switch: self.closeCommandsLaier()
		if self.chk_banderas(False, True):
			# Obtiene el texto seleccionado
			temp = getSelectedText(api.getCaretObject())
			if not temp['success'] or temp['data'] == '':
				LaunchThread(self, 9).start()
			else:
				LaunchThread(self, 9, temp['data']).start()

class LaunchThread(Thread):
	"""
	Clase para gestionar la ejecución de diferentes diálogos en hilos separados.
	"""
	def __init__(self, frame, option, text=None):
		"""
		Inicializa el hilo con las opciones proporcionadas.

		:param frame: El marco principal.
		:param option: La opción a ejecutar.
		:param text: El texto a traducir, si aplica.
		"""
		super(LaunchThread, self).__init__()

		self.frame = frame
		self.option = option
		self.text = text
		self.daemon = True

	def run(self):
		"""
		Ejecuta la opción seleccionada en un hilo separado.
		"""
		def appLauncherAjustes():
			"""
			Lanza el diálogo de configuración.
			"""
			self._main = ConfigDialog(gui.mainFrame, self.frame)
			gui.mainFrame.prePopup()
			self._main.Show()

		def change_origen():
			"""
			Cambia el idioma de origen.
			"""
			gui.mainFrame.prePopup()
			dlg = DialogoLang(None, self.frame, 0)
			dlg.ShowModal()
			dlg.Destroy()
			gui.mainFrame.postPopup()

		def change_destino():
			"""
			Cambia el idioma de destino.
			"""
			gui.mainFrame.prePopup()
			dlg = DialogoLang(None, self.frame, 1)
			dlg.ShowModal()
			dlg.Destroy()
			gui.mainFrame.postPopup()

		def change_traductor():
			"""
			Cambia el módulo de traducción.
			"""
			gui.mainFrame.prePopup()
			dlg = DialogoLang(None, self.frame, 2)
			dlg.ShowModal()
			dlg.Destroy()
			gui.mainFrame.postPopup()

		def translate_select():
			"""
			Traduce el texto almacenado en el atributo `self.text`.

			Abre un cuadro de diálogo de progreso mientras se realiza la traducción.
			Si la traducción es exitosa y el resultado no es el mismo que el texto original, muestra el resultado de la traducción.
			Si no se pudo obtener la traducción o ocurrió un error, muestra un mensaje informativo o de error.

			Resultado:
				Inicia el proceso de traducción del texto y maneja el diálogo de resultados.
			"""
			self.progress_dialog = ProgressDialog(self.frame, self.text)
			result = self.progress_dialog.ShowModal()
			if result == wx.ID_OK:
				self.frame.gestor_settings.is_active_translate = False
				if self.progress_dialog.completed:
					if not self.progress_dialog.traduccion_resultado or self.text == self.progress_dialog.traduccion_resultado:
						gui.messageBox(_("No se ha podido obtener la traducción de lo seleccionado."), _("Información"), wx.ICON_INFORMATION)
						return
					show_translation_result(self.progress_dialog.traduccion_resultado)
				else:
					self.frame.gestor_settings.is_active_translate = False
					gui.messageBox(_("Hubo un error en la traducción:\n\n") + self.progress_dialog.error, _("Error"), wx.OK | wx.ICON_ERROR)
			elif result == wx.ID_CANCEL:
				self.frame.gestor_settings.is_active_translate = False
				gui.messageBox(_("La traducción fue cancelada por el usuario."), _("Cancelado"), wx.OK | wx.ICON_INFORMATION)

		def show_translation_result(data):
			"""
			Muestra el diálogo con el resultado de la traducción o copia al portapapeles segun configuración
			"""
			if self.frame.gestor_settings.chkResults:
				self.frame.gestor_portapapeles.set_clipboard_text(data)
				mute(0.3, _("Traducción copiada al portapapeles"))
			else:
				gui.mainFrame.prePopup()
				dlg = DialogResults(None, _("Resultado de la traducción"), data)
				dlg.ShowModal()
				dlg.Destroy()
				gui.mainFrame.postPopup()

		def translate_history():
			"""
			Muestra el historial de traducción.
			"""
			gui.mainFrame.prePopup()
			dlg = DialogHistory(None, self.frame)
			dlg.ShowModal()
			dlg.Destroy()
			gui.mainFrame.postPopup()

		def translate_update():
			"""
			Actualiza idiomas del complemento.
			"""
			datos = self.frame.gestor_repositorio.comprobar_nuevos_y_actualizaciones()
			if datos['success']:
				self.update_dialog = UpdateDialog(self.frame, datos['data'])
				result = self.update_dialog.ShowModal()
				if result == wx.ID_OK:
					dlg = ProgresoDescargaInstalacion(self.frame, datos['data'])
					dlg.ShowModal()
					dlg.Destroy()
				else:
					return
			else: # No hay actualizaciones.
				self.frame.gestor_settings.IS_WinON = True
				if 'error' in datos and not datos['error']:
					gui.messageBox(datos['data'], _("Información"), wx.ICON_INFORMATION)
				else:
					gui.messageBox(datos['data'], _("Error"), wx.OK | wx.ICON_ERROR)
				self.frame.gestor_settings.IS_WinON = False

		def detect_lang():
			"""
			Detecta el idioma del texto almacenado en el atributo `self.text`.

			Acciones:
				Llama al método `detector_idiomas` del objeto `gestor_translate` de `self.frame` 
				para detectar el idioma del texto.

			Resultado:
				Inicia el proceso de detección de idioma para el texto proporcionado.
			"""
			self.frame.gestor_translate.detector_idiomas(self.text)

		def gui_translate():
			"""
			Abre el diálogo de la interfaz de traducción.

			Inicializa la interfaz de traducción con el texto almacenado en el atributo `self.text` si está disponible.
			Permite al usuario interactuar con la interfaz de traducción de la GUI.

			Resultado:
				Muestra el diálogo de la interfaz de traducción.
			"""
			self._main = TranslateDialog(gui.mainFrame, self.frame, self.text)
			gui.mainFrame.prePopup()
			self._main.Show()

		if self.option == 1: # Configuración
			wx.CallAfter(appLauncherAjustes)
		elif self.option == 2: # Cambiar idioma origen
			wx.CallAfter(change_origen)
		elif self.option == 3: # Cambiar idioma destino
			wx.CallAfter(change_destino)
		elif self.option == 4: # Cambiar modulo traducción destino
			wx.CallAfter(change_traductor)
		elif self.option == 5: # Traducir seleccionado
			wx.CallAfter(translate_select)
		elif self.option == 6: # Historial de traducción
			wx.CallAfter(translate_history)
		elif self.option == 7: # Actualizaciones de idioma del complemento
			wx.CallAfter(translate_update)
		elif self.option == 8: # Detecta idioma seleccionado
			wx.CallAfter(detect_lang)
		elif self.option == 9: # GUI Traductor seleccionado
			wx.CallAfter(gui_translate)

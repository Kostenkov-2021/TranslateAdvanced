# -*- coding: utf-8 -*-
# Copyright (C) 2024 Héctor J. Benítez Corredera <xebolax@gmail.com>
# Este archivo está cubierto por la Licencia Pública General de GNU.
#
# Carga NVDA
import addonHandler
import languageHandler
import gui
# Carga Python
import wx
# Carga personal
from ..managers.managers_dict import LanguageDictionary

# Carga traducción
addonHandler.initTranslation()

class ConfigDialog(wx.Dialog):
	"""
	Diálogo de configuración basado en wx.Listbook.
	"""
	def __init__(self, parent, frame):
		"""
		Inicializa el diálogo de configuración.

		:param parent: El panel padre del diálogo.
		:param frame: El marco principal de la aplicación.
		"""
		super(ConfigDialog, self).__init__(parent, title=_("Configuración de Traductor Avanzado"), size=(800, 600))

		self.frame = frame
		self.frame.gestor_ayuda.ayudas = {}
		self.frame.gestor_settings.IS_WinON = True
		# Variables para datos de lenguaje
		self.datos = LanguageDictionary(self.frame.gestor_lang.obtener_idiomas("google"))
		self.idiomas_code = self.datos.get_keys()
		self.idiomas_name = self.datos.get_values()
		self.destino_default = self.frame.gestor_settings.choiceLangDestino_google_def
		self.destino_alternate = self.frame.gestor_settings.choiceLangDestino_google_alt

		self.api_manager = self.frame.gestor_apis
		# Variable para rastrear el traductor seleccionado y su API por defecto
		self.selected_service = None
		self.default_api_index = {"deepL_free": self.frame.gestor_settings.api_deepl, "deepL_pro": self.frame.gestor_settings.api_deepl_pro, "libre_translate": self.frame.gestor_settings.api_libretranslate, "openai": self.frame.gestor_settings.api_openai}
		# Crear el Listbook
		self.listbook = wx.Listbook(self, wx.ID_ANY)

		# Añadir las páginas al Listbook
		self.listbook.AddPage(self.create_general_page(self.listbook), _("General"))
		self.listbook.AddPage(self.create_online_translator_page(self.listbook), _("Módulos de traducción"))
		# Botones Aceptar y Cancelar
		self.ok_button = wx.Button(self, wx.ID_OK, label=_("&Aceptar"))
		self.cancel_button = wx.Button(self, wx.ID_CANCEL, label=_("&Cancelar"))

		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		button_sizer.Add(self.ok_button, 0, wx.ALL, 10)
		button_sizer.Add(self.cancel_button, 0, wx.ALL, 10)

		# Sizer principal
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		main_sizer.Add(self.listbook, 1, wx.EXPAND | wx.ALL, 10)
		main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

		self.SetSizer(main_sizer)

		self.CenterOnScreen()

		# Llamar a la función para inicializar los bindings de los widgets
		self.init_bindings()
		self.start__init__()

		# Bind para detectar cambio de página
		self.listbook.Bind(wx.EVT_LISTBOOK_PAGE_CHANGED, self.on_page_changed)
		self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)

	def SetHelp(self, widget, text):
		"""
		Establece un mensaje de ayuda para un widget específico.

		:param widget: El widget al cual se le asignará el mensaje de ayuda.
		:param text: El texto del mensaje de ayuda que se mostrará cuando el widget reciba el enfoque y se presione Ctrl+H.
		"""
		self.frame.gestor_ayuda.agregar_ayuda(widget, text)

	def agregar_ayudas(self):
		"""
		Establece los textos de ayuda para todos los widgets de la interfaz.
		"""
		self.SetHelp(self.cache_checkbox, _("Activa o desactiva el uso de la caché de traducción. Esta opción almacena traducciones anteriores para mejorar la velocidad y eficiencia."))
		self.SetHelp(self.results_checkbox, _("Activa o desactiva la visualización del diálogo de resultados y copia el resultado al portapapeles. Esto permite revisar y utilizar las traducciones de manera rápida."))
		self.SetHelp(self.change_lang_checkbox, _("Activa el intercambio automático si el origen detectado coincide con el destino (experimental). Si se detecta que el idioma del texto de origen es el mismo que el de destino, el traductor cambiará automáticamente el idioma de destino para evitar traducciones innecesarias."))
		self.SetHelp(self.default_choice_lang, _("Selecciona el idioma por defecto para las traducciones. Este es el idioma principal al que se traducirán los textos por defecto. Ejemplo: Inglés - en."))
		self.SetHelp(self.alternate_choice_lang, _("Selecciona el idioma alternativo para las traducciones. Este idioma se utilizará cuando se active la opción de intercambio automático. Ejemplo: Español - es."))
		self.SetHelp(self.translator_choice, _("Selecciona el traductor online que deseas utilizar. Puedes elegir entre diferentes servicios de traducción disponibles."))
		self.SetHelp(self.api_listbox, _("Muestra las claves API disponibles para el traductor seleccionado. Las claves API permiten autenticar y utilizar los servicios de traducción."))
		self.SetHelp(self.add_button, _("Añade una nueva clave API. Esto es necesario para utilizar servicios de traducción que requieren autenticación."))
		self.SetHelp(self.edit_button, _("Edita la clave API seleccionada. Permite modificar los detalles de una clave API existente."))
		self.SetHelp(self.delete_button, _("Elimina la clave API seleccionada. Esto eliminará la clave de la lista y ya no se podrá utilizar para autenticar servicios de traducción."))
		self.SetHelp(self.default_button, _("Establece la clave API seleccionada como predeterminada. Esta clave se utilizará por defecto para el servicio de traducción seleccionado."))
		self.SetHelp(self.listbook, _("Navega entre las diferentes secciones de configuración. Permite cambiar entre las configuraciones generales y las específicas del traductor."))
		self.SetHelp(self.ok_button, _("Guarda los cambios y cierra el diálogo de configuración. Asegúrate de revisar todas las opciones antes de confirmar."))
		self.SetHelp(self.cancel_button, _("Descarta los cambios y cierra el diálogo de configuración. Los cambios realizados no serán guardados."))

		# Asegurar que los paneles del Listbook tengan ayuda específica
		for i in range(self.listbook.GetPageCount()):
			page = self.listbook.GetPage(i)
			page_text = self.listbook.GetPageText(i)
			if page_text == _("General"):
				self.SetHelp(page, _("Configuración general del traductor. Aquí puedes ajustar las opciones básicas y el comportamiento del traductor."))
			elif page_text == _("Módulos de traducción"):
				self.SetHelp(page, _("Gestión de los módulos de traducción online. Permite configurar los servicios de traducción y sus claves API."))
			else:
				self.SetHelp(page, _("Panel de configuración: ") + page_text)

	def on_page_changed(self, event):
		"""
		Maneja el evento de cambio de página en el Listbook.

		:param event: Evento de cambio de página.
		"""
		new_page = event.GetSelection()
		old_page = event.GetOldSelection()

		# Aquí puedes definir las acciones a realizar cuando cambies de página
		if new_page == 0:  # Página General
			self.handle_general_page()
		elif new_page == 1:  # Página Traductor Online
			self.handle_online_translator_page()
		# Llamar al evento predeterminado
		event.Skip()

	def handle_general_page(self):
		"""
		Maneja las acciones específicas para la página General.
		"""
		pass

	def handle_online_translator_page(self):
		"""
		Maneja las acciones específicas para la página Traductor Online.
		"""
		pass #self.update_api_list()

	def create_general_page(self, parent):
		"""
		Crea la página General.

		:param parent: El panel padre donde se añadirá la página.
		:return: Un panel con los widgets de configuración de la página General.
		"""
		panel = wx.Panel(parent)
		sizer = wx.BoxSizer(wx.VERTICAL)

		# Checkbox para activar o desactivar la caché de traducción
		self.cache_checkbox = wx.CheckBox(panel, label=_("Usar caché &de traducción"))
		sizer.Add(self.cache_checkbox, 0, wx.ALL, 10)

		# Checkbox para mostrar dialogo de resultados
		self.results_checkbox = wx.CheckBox(panel, label=_("No mostrar dialogo de &resultados y copiar al portapapeles"))
		sizer.Add(self.results_checkbox, 0, wx.ALL, 10)

		# Checkbox para activar intercambio de lenguajes
		self.change_lang_checkbox = wx.CheckBox(panel, label=_("Activar el &intercambio automático si el origen detectado coincide con el destino (experimental)"))
		sizer.Add(self.change_lang_checkbox, 0, wx.ALL, 10)

		# Choice para seleccionar el lenguaje por defecto
		default_label_lang = wx.StaticText(panel, label=_("Idioma de la &traducción:"))
		sizer.Add(default_label_lang, 0, wx.ALL, 10)
		self.default_choice_lang = wx.Choice(panel, choices=[f"{self.descripcion_lenguaje(i) if self.descripcion_lenguaje(i) else self.idiomas_name[self.idiomas_code.index(i)]} - {i}" for i in self.idiomas_code])
		sizer.Add(self.default_choice_lang, 0, wx.ALL, 10)

		# Choice para seleccionar el lenguaje alternativo
		alternate_label_lang = wx.StaticText(panel, label=_("Idioma a&lternativo:"))
		sizer.Add(alternate_label_lang, 0, wx.ALL, 10)
		self.alternate_choice_lang = wx.Choice(panel, choices=[])
		sizer.Add(self.alternate_choice_lang, 0, wx.ALL, 10)

		panel.SetSizer(sizer)
		return panel

	def create_online_translator_page(self, parent):
		"""
		Crea la página Traductor Online.

		:param parent: El panel padre donde se añadirá la página.
		:return: Un panel con los widgets de configuración de la página Traductor Online.
		"""
		panel = wx.Panel(parent)
		sizer = wx.BoxSizer(wx.VERTICAL)

		# Choice para seleccionar el traductor online
		transonline = wx.StaticText(panel, label=_("&Elija un traductor online:"))
		sizer.Add(transonline, 0, wx.ALL, 10)
		self.translator_choice = wx.Choice(panel, choices=self.frame.gestor_settings.servers_names)
		sizer.Add(self.translator_choice, 0, wx.ALL, 10)

		# Listbox para mostrar las claves API
		apilabel = wx.StaticText(panel, label=_("&Gestor de APIS:"))
		sizer.Add(apilabel, 0, wx.ALL, 10)

		self.api_listbox = wx.ListBox(panel)
		sizer.Add(self.api_listbox, 1, wx.EXPAND | wx.ALL, 10)
		
		# Botones para gestionar las claves API
		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.add_button = wx.Button(panel, label=_("Añadir\tF1"))
		self.edit_button = wx.Button(panel, label=_("Editar\tF2"))
		self.delete_button = wx.Button(panel, label=_("Eliminar\tF3"))
		self.default_button = wx.Button(panel, label=_("Por defecto\tF4"))

		button_sizer.Add(self.add_button, 1, wx.ALL, 5)
		button_sizer.Add(self.edit_button, 1, wx.ALL, 5)
		button_sizer.Add(self.delete_button, 1, wx.ALL, 5)
		button_sizer.Add(self.default_button, 1, wx.ALL, 5)

		sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

		panel.SetSizer(sizer)

		self.api_controls = (self.api_listbox, self.add_button, self.edit_button, self.delete_button, self.default_button)
		self.show_api_controls(False)

		return panel

	def init_bindings(self):
		"""
		Inicializa los bindings de los widgets.
		"""
		# Bind de Módulos de traducción
		self.translator_choice.Bind(wx.EVT_CHOICE, self.on_translator_choice)
		self.add_button.Bind(wx.EVT_BUTTON, self.on_add_api)
		self.edit_button.Bind(wx.EVT_BUTTON, self.on_edit_api)
		self.delete_button.Bind(wx.EVT_BUTTON, self.on_delete_api)
		self.default_button.Bind(wx.EVT_BUTTON, self.on_set_default)
		# Bind de botones generales
		self.Bind(wx.EVT_BUTTON, self.on_accept, id=wx.ID_OK)
		self.Bind(wx.EVT_BUTTON, self.on_cancel, id=wx.ID_CANCEL)
		# Bind para actualizar idioma alternativo
		self.default_choice_lang.Bind(wx.EVT_CHOICE, self.on_default_lang_change)
		# Bind para activar/desactivar selección de idioma
		self.change_lang_checkbox.Bind(wx.EVT_CHECKBOX, self.on_alternate_lang_toggle)

	def descripcion_lenguaje(self, code):
		"""
		Devuelve la descripción del lenguaje basado en el código proporcionado.

		:param code: Código del lenguaje a describir.
		:return: Descripción del lenguaje.
		"""
		return languageHandler.getLanguageDescription(code)

	def show_api_controls(self, show):
		"""
		Muestra u oculta los controles de API.

		:param show: Booleano que indica si se deben mostrar los controles.
		"""
		for control in self.api_controls:
			control.Show(show)
		self.Layout()

	def update_api_list(self):
		"""
		Actualiza la lista de claves API según el traductor seleccionado.
		"""
		self.api_listbox.Clear()
		default_index = None
		if self.selected_service and self.selected_service in ["deepL_free", "deepL_pro", "libre_translate", "openai"]:
			apis = self.api_manager.get_apis(self.selected_service)
			if apis:
				for i, api in enumerate(apis):
					display_text = api['name']
					if self.selected_service == "libre_translate":
						display_text += f" ({api['url']})"
					if i == self.default_api_index[self.selected_service]:
						display_text += " *"
						default_index = i
					self.api_listbox.Append(display_text)
			else:
				self.api_listbox.Append(_("No existe ninguna API para este servicio."))
		if default_index is not None:
			self.api_listbox.SetSelection(default_index)
		else:
			self.api_listbox.SetSelection(0)

		self.frame.gestor_settings.api_deepl = self.default_api_index["deepL_free"]
		self.frame.gestor_settings.api_deepl_pro = self.default_api_index["deepL_pro"]
		self.frame.gestor_settings.api_libretranslate = self.default_api_index["libre_translate"]
		self.frame.gestor_settings.api_openai = self.default_api_index["openai"]
		self.frame.gestor_settings.guardaConfiguracion()

	def actualizar_aceleradores(self, habilitar):
		"""
		Habilita o deshabilita las teclas aceleradoras F1, F2, F3 y F4.

		:param habilitar: Booleano que indica si se deben habilitar o deshabilitar las teclas aceleradoras.
		"""
		if habilitar:
			accel_tbl = wx.AcceleratorTable([
				(wx.ACCEL_NORMAL, wx.WXK_F1, self.add_button.GetId()),
				(wx.ACCEL_NORMAL, wx.WXK_F2, self.edit_button.GetId()),
				(wx.ACCEL_NORMAL, wx.WXK_F3, self.delete_button.GetId()),
				(wx.ACCEL_NORMAL, wx.WXK_F4, self.default_button.GetId())
			])
		else:
			accel_tbl = wx.AcceleratorTable([])
		self.SetAcceleratorTable(accel_tbl)

	def on_translator_choice(self, event):
		"""
		Maneja el evento de selección de traductor online.

		:param event: Evento de selección.
		"""
		if event.GetString() not in [_("Traductor DeepL (API Free *)"), _("Traductor DeepL (API Pro *)"), _("Traductor LibreTranslate (API *)"), _("Traductor OpenAI GPT4o-mini (API *)")]:
			self.show_api_controls(False)
			self.actualizar_aceleradores(False)
			return
		choice = event.GetString()
		self.selected_service = self.frame.gestor_settings.service_map.get(choice)
		if self.selected_service:
			self.show_api_controls(True)
			self.actualizar_aceleradores(True)
		else:
			self.show_api_controls(False)
			self.actualizar_aceleradores(False)
		self.update_api_list()

	def GetSelectionChoice(self):
		"""
	Obtiene la selección actual del mapa de servicios.
		"""
		return self.frame.gestor_settings.service_map_selection.get(self.translator_choice.GetString(self.translator_choice.GetSelection()))

	def select_choice_by_value(self, value):
		# Invertir el diccionario para buscar por valor
		inverted_dict = {v: k for k, v in self.frame.gestor_settings.service_map_selection.items()}
		# Obtener el nombre basado en el valor
		service_name = inverted_dict.get(value, None)
		if service_name:
			# Seleccionar el ítem en wx.Choice por el nombre
			self.translator_choice.SetStringSelection(service_name)

	def on_default_lang_change(self, event):
		"""
		Maneja el evento de cambio de selección en el wx.Choice de idioma por defecto.
		Actualiza el wx.Choice de idioma alternativo para excluir el idioma seleccionado por defecto.

		:param event: Evento de cambio de selección.
		"""
		self.update_alternate_choices()

	def update_alternate_choices(self):
		"""
		Actualiza las opciones del wx.Choice de idioma alternativo para excluir el idioma seleccionado por defecto.
		"""
		selected_default = self.default_choice_lang.GetStringSelection().split(" - ")[1]
		choices = [f"{self.descripcion_lenguaje(i) if self.descripcion_lenguaje(i) else self.idiomas_name[self.idiomas_code.index(i)]} - {i}" for i in self.idiomas_code if i != selected_default]
		self.alternate_choice_lang.Clear()
		self.alternate_choice_lang.AppendItems(choices)
		# Mantener la selección anterior si está disponible, de lo contrario seleccionar el primer elemento
		previous_selection = self.frame.gestor_settings.choiceLangDestino_google_alt
		if previous_selection and previous_selection in self.idiomas_code and previous_selection != selected_default:
			self.alternate_choice_lang.SetStringSelection(f"{self.descripcion_lenguaje(previous_selection) if self.descripcion_lenguaje(previous_selection) else self.idiomas_name[self.idiomas_code.index(previous_selection)]} - {previous_selection}")
		else:
			self.alternate_choice_lang.SetSelection(0)

	def on_alternate_lang_toggle(self, event):
		"""
		Maneja el evento de activación/desactivación de la casilla de uso del mismo idioma.
		:param event: Evento de cambio de estado.
		"""
		enabled = self.change_lang_checkbox.GetValue()
		self.default_choice_lang.Enable(enabled)
		self.alternate_choice_lang.Enable(enabled)
		if enabled:
			self.update_alternate_choices()

	def start__init__(self):
		"""
		Inicializa las configuraciones generales y del traductor online.
		"""
		self.start_general()
		self.start_translate_online()
		self.agregar_ayudas()

	def start_general(self):
		"""
		Inicializa la configuración general del diálogo.
		"""
		self.cache_checkbox.SetValue(self.frame.gestor_settings.chkCache)
		self.results_checkbox.SetValue(self.frame.gestor_settings.chkResults)
		nombre_lenguaje = self.descripcion_lenguaje(self.destino_default) or self.idiomas_name[self.idiomas_code.index(self.destino_default)]
		self.default_choice_lang.SetSelection(self.idiomas_code.index(self.destino_default))

		# Inicializar casilla de uso del mismo idioma
		self.change_lang_checkbox.SetValue(self.frame.gestor_settings.chkAltLang)
		enabled = self.frame.gestor_settings.chkAltLang
		self.default_choice_lang.Enable(enabled)
		self.alternate_choice_lang.Enable(enabled)
		
		if enabled:
			# Inicializar idioma alternativo
			selected_default = self.destino_default
			choices = [f"{self.descripcion_lenguaje(i) if self.descripcion_lenguaje(i) else self.idiomas_name[self.idiomas_code.index(i)]} - {i}" for i in self.idiomas_code if i != selected_default]
			self.alternate_choice_lang.Clear()
			self.alternate_choice_lang.AppendItems(choices)
			previous_selection = self.destino_alternate
			if previous_selection and previous_selection in self.idiomas_code and previous_selection != selected_default:
				self.alternate_choice_lang.SetStringSelection(f"{self.descripcion_lenguaje(previous_selection) if self.descripcion_lenguaje(previous_selection) else self.idiomas_name[self.idiomas_code.index(previous_selection)]} - {previous_selection}")
			else:
				self.alternate_choice_lang.SetSelection(0)

	def start_translate_online(self):
		"""
		Inicializa la configuración del traductor online del diálogo.
		"""
		self.select_choice_by_value(self.frame.gestor_settings.choiceOnline)
		if self.frame.gestor_settings.choiceOnline in [4, 5, 6, 9]:
			choice = self.translator_choice.GetStringSelection()
			self.selected_service = self.frame.gestor_settings.service_map.get(choice)
			if self.selected_service:
				self.show_api_controls(True)
				self.update_api_list()
			else:
				self.show_api_controls(False)

	def on_add_api(self, event):
		"""
		Maneja el evento de añadir una nueva clave API.

		:param event: Evento de botón.
		"""
		if self.selected_service:
			self.show_api_dialog(_("Añadir API"), "add")
			# Si es la única API, marcarla como predeterminada
			if len(self.api_manager.get_apis(self.selected_service)) == 1:
				self.default_api_index[self.selected_service] = 0
			self.update_api_list()

	def on_edit_api(self, event):
		"""
		Maneja el evento de editar una clave API existente.

		:param event: Evento de botón.
		"""
		if not self.selected_service or self.api_listbox.GetSelection() == wx.NOT_FOUND or not self.api_manager.get_apis(self.selected_service):
			wx.MessageBox(_("No existe ninguna API para este servicio. Por favor, añada una API primero."), _("Error"), wx.OK | wx.ICON_ERROR)
			return
		self.show_api_dialog(_("Editar API"), "edit", self.api_listbox.GetSelection())

	def on_delete_api(self, event):
		"""
		Maneja el evento de eliminar una clave API.

		:param event: Evento de botón.
		"""
		if not self.selected_service or self.api_listbox.GetSelection() == wx.NOT_FOUND or not self.api_manager.get_apis(self.selected_service):
			wx.MessageBox(_("No existe ninguna API para este servicio. Por favor, añada una API primero."), _("Error"), wx.OK | wx.ICON_ERROR)
			return
		dialog = wx.MessageDialog(self, _("¿Estás seguro de que deseas eliminar esta clave API?"), _("Confirmación"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
		if dialog.ShowModal() == wx.ID_YES:
			self.api_manager.delete_api(self.selected_service, self.api_listbox.GetSelection())
			apis = self.api_manager.get_apis(self.selected_service)
			if not apis:
				self.default_api_index[self.selected_service] = None
			else:
				self.default_api_index[self.selected_service] = 0
			self.update_api_list()
		self.api_listbox.SetFocus()

	def on_set_default(self, event):
		"""
		Maneja el evento de establecer una clave API por defecto.

		:param event: Evento de botón.
		"""
		if not self.selected_service or self.api_listbox.GetSelection() == wx.NOT_FOUND or not self.api_manager.get_apis(self.selected_service):
			wx.MessageBox(_("No existe ninguna API para este servicio. Por favor, añada una API primero."), _("Error"), wx.OK | wx.ICON_ERROR)
			return
		self.default_api_index[self.selected_service] = self.api_listbox.GetSelection()
		self.update_api_list()
		self.api_listbox.SetFocus()

	def show_api_dialog(self, title, action, index=None):
		"""
		Muestra el diálogo para añadir o editar una clave API.

		:param title: Título del diálogo.
		:param action: Acción a realizar (add o edit).
		:param index: Índice de la clave a editar (solo para edit).
		"""
		dialog = wx.Dialog(self, title=title, size=(400, 300))

		sizer = wx.BoxSizer(wx.VERTICAL)
		name_label = wx.StaticText(dialog, label=_("&Nombre:"))
		name_text = wx.TextCtrl(dialog)
		key_label = wx.StaticText(dialog, label=_("Clave &API:"))
		key_text = wx.TextCtrl(dialog)

		sizer.Add(name_label, 0, wx.ALL, 5)
		sizer.Add(name_text, 0, wx.ALL | wx.EXPAND, 5)
		sizer.Add(key_label, 0, wx.ALL, 5)
		sizer.Add(key_text, 0, wx.ALL | wx.EXPAND, 5)

		url_text = None
		if self.selected_service == "libre_translate":
			url_label = wx.StaticText(dialog, label=_("&URL:"))
			url_text = wx.TextCtrl(dialog)
			url_text.SetValue("https://translate.nvda.es/translate")
			sizer.Add(url_label, 0, wx.ALL, 5)
			sizer.Add(url_text, 0, wx.ALL | wx.EXPAND, 5)

		ok_button = wx.Button(dialog, wx.ID_OK, _("&Aceptar"))
		cancel_button = wx.Button(dialog, wx.ID_CANCEL, _("&Cancelar"))
		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		button_sizer.Add(ok_button, 1, wx.ALL, 5)
		button_sizer.Add(cancel_button, 1, wx.ALL, 5)
		sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

		dialog.SetSizer(sizer)

		if action == "edit" and index is not None:
			api = self.api_manager.get_api(self.selected_service, index)
			name_text.SetValue(api["name"])
			key_text.SetValue(api["key"])
			if url_text:
				url_text.Clear()
				url_text.SetValue(api["url"])

		# Agregar ayudas
		self.SetHelp(name_text, _("Introduce el nombre para identificar esta clave API."))
		self.SetHelp(key_text, _("Introduce la clave API proporcionada por el servicio de traducción."))
		if url_text:
			self.SetHelp(url_text, _("Introduce la URL del servidor de traducción LibreTranslate. Esta URL se utilizará para enviar las solicitudes de traducción."))
		self.SetHelp(ok_button, _("Guarda la clave API y cierra el diálogo."))
		self.SetHelp(cancel_button, _("Descarta los cambios y cierra el diálogo."))

		# Centrar el diálogo en la pantalla
		dialog.CenterOnScreen()

		while True:
			if dialog.ShowModal() == wx.ID_OK:
				name = name_text.GetValue().strip()
				key = key_text.GetValue().strip()
				url = url_text.GetValue().strip() if url_text else None
				if not name or not key or (url_text and not url):
					wx.MessageBox(_("Todos los campos son obligatorios."), _("Error"), wx.OK | wx.ICON_ERROR)
					continue
				else:
					if action == "add":
						self.api_manager.add_api(self.selected_service, name, key, url)
						if len(self.api_manager.get_apis(self.selected_service)) == 1:
							self.default_api_index[self.selected_service] = 0
					elif action == "edit" and index is not None:
						self.api_manager.edit_api(self.selected_service, index, name, key, url)
					self.update_api_list()
			break
		dialog.Destroy()
		self.api_listbox.SetFocus()

	def on_accept(self, event):
		"""
		Maneja el evento de aceptación del diálogo.

		:param event: Evento de botón.
		"""
		self.frame.gestor_settings.chkCache = self.cache_checkbox.GetValue()
		self.frame.gestor_settings.chkResults = self.results_checkbox.GetValue()
		self.frame.gestor_settings.chkAltLang = self.change_lang_checkbox.GetValue()
		if self.frame.gestor_settings.chkAltLang:
			self.frame.gestor_settings.choiceLangDestino_google_def = self.default_choice_lang.GetString(self.default_choice_lang.GetSelection()).split()[-1:][0]
			self.frame.gestor_settings.choiceLangDestino_google_alt = self.alternate_choice_lang.GetString(self.alternate_choice_lang.GetSelection()).split()[-1:][0]

		self.frame.gestor_settings.choiceOnline = self.GetSelectionChoice()
		self.frame.gestor_settings.api_deepl = self.default_api_index["deepL_free"]
		self.frame.gestor_settings.api_deepl_pro = self.default_api_index["deepL_pro"]
		self.frame.gestor_settings.api_libretranslate = self.default_api_index["libre_translate"]
		self.frame.gestor_settings.api_openai = self.default_api_index["openai"]

		self.frame.gestor_settings.IS_WinON = False
		self.frame.gestor_settings.guardaConfiguracion()

		self.Destroy()
		gui.mainFrame.postPopup()

	def on_cancel(self, event):
		"""
		Maneja el evento de cancelación del diálogo.

		:param event: Evento de botón.
		"""
		self.frame.gestor_settings.IS_WinON = False
		self.Destroy()
		gui.mainFrame.postPopup()

	def onKeyPress(self, event):
		"""
		Maneja el evento de presión de teclas.

		:param event: El evento de presión de tecla.
		"""
		if event.ControlDown() and event.GetKeyCode() == ord('H'):
			widget_focused = wx.Window.FindFocus()
			if widget_focused:
				if self.frame.gestor_ayuda.ayuda_existe(widget_focused):
					self.frame.gestor_ayuda.mostrar_ayuda(widget_focused)
				elif isinstance(widget_focused.GetParent(), wx.Listbook):
					selected_page_index = self.listbook.GetSelection()
					selected_page = self.listbook.GetPage(selected_page_index)
					if self.frame.gestor_ayuda.ayuda_existe(selected_page):
						self.frame.gestor_ayuda.mostrar_ayuda(selected_page)
					else:
						wx.MessageBox(_("No hay ayuda disponible para este elemento."), _("Ayuda"), wx.OK | wx.ICON_INFORMATION)
				else:
					wx.MessageBox(_("No hay ayuda disponible para este elemento."), _("Ayuda"), wx.OK | wx.ICON_INFORMATION)
			else:
				wx.MessageBox(_("No hay un elemento enfocado."), _("Ayuda"), wx.OK | wx.ICON_INFORMATION)
		else:
			event.Skip()

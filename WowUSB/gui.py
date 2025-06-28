#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

import os
import time
import threading

import wx
import wx.adv

import WowUSB.core as core
import WowUSB.list_devices as list_devices
import WowUSB.miscellaneous as miscellaneous

data_directory = os.path.dirname(__file__) + "/data/"

app = wx.App()

_ = miscellaneous.i18n


class MainFrame(wx.Frame):
    __MainPanel = None
    __MenuBar = None

    __menuItemShowAll = None
    __filesystem_choice = None
    __fs_panel = None

    def __init__(self, title, pos, size, style=wx.DEFAULT_FRAME_STYLE):
        super(MainFrame, self).__init__(None, -1, title, pos, size, style)

        self.SetIcon(wx.Icon(data_directory + "icon.ico"))

        file_menu = wx.Menu()
        self.__menuItemShowAll = wx.MenuItem(file_menu, wx.ID_ANY, _("Show all drives") + " \tCtrl+A",
                                          _("Show all drives, even those not detected as USB stick."),
                                          wx.ITEM_CHECK)
        file_menu.Append(self.__menuItemShowAll)

        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT)

        help_menu = wx.Menu()
        help_item = help_menu.Append(wx.ID_ABOUT)

        options_menu = wx.Menu()
        self.options_boot = wx.MenuItem(options_menu, wx.ID_ANY, _("Set boot flag"),
                                     _("Sets boot flag after process of copying."),
                                     wx.ITEM_CHECK)
        self.options_skip_grub = wx.MenuItem(options_menu, wx.ID_ANY, _("Skip legacy grub bootloader"),
                                          _("No legacy grub bootloader will be created. NOTE: It will only boot on system with UEFI support."),
                                          wx.ITEM_CHECK)

        # Create filesystem selection panel
        self.__fs_panel = wx.Panel(self)
        fs_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        fs_label = wx.StaticText(self.__fs_panel, label=_("Target Filesystem:"))
        # Filesystem choices for standard mode. Multiboot will have its own or imply F2FS/EXFAT etc.
        self.__filesystem_choice = wx.Choice(self.__fs_panel, choices=[
            _("Auto Detect"), # New default
            _("FAT32 (Most compatible, <4GB files)"),
            _("NTFS (Windows native, >4GB files)"),
            _("exFAT (Modern, >4GB files, good for flash)"),
            _("F2FS (Flash-friendly, >4GB files)"),
            _("BTRFS (Advanced, >4GB files)")
        ])
        self.__filesystem_choice.SetSelection(0) # Default to Auto Detect
        
        fs_sizer.Add(fs_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        fs_sizer.Add(self.__filesystem_choice, 1, wx.EXPAND)
        self.__fs_panel.SetSizer(fs_sizer)

        options_menu.Append(self.options_boot)
        options_menu.Append(self.options_skip_grub)
        options_menu.AppendSeparator()
        self.menuItemAdvancedMode = wx.MenuItem(options_menu, wx.ID_ANY, _("Advanced Mode"),
                                                _("Show advanced configuration options."),
                                                wx.ITEM_CHECK)
        options_menu.Append(self.menuItemAdvancedMode)


        self.__MenuBar = wx.MenuBar()
        self.__MenuBar.Append(file_menu, _("&File"))
        self.__MenuBar.Append(options_menu, _("&Options"))
        self.__MenuBar.Append(help_menu, _("&Help"))

        self.SetMenuBar(self.__MenuBar)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Multiboot Enable Checkbox
        self.cb_enable_multiboot = wx.CheckBox(self, label=_("Enable Multiboot Mode"))
        main_sizer.Add(self.cb_enable_multiboot, 0, wx.ALL | wx.EXPAND, 5)
        self.cb_enable_multiboot.Bind(wx.EVT_CHECKBOX, self.on_toggle_multiboot_mode)

        # Add filesystem selection panel to the top (for standard mode)
        main_sizer.Add(self.__fs_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)


        # Placeholder for Partition Visualization Panel
        self.visualization_panel = wx.Panel(self, style=wx.BORDER_SUNKEN)
        self.visualization_panel.SetMinSize(wx.Size(-1, 60)) # Height of 60, width flexible
        self.visualization_panel.SetBackgroundColour(wx.Colour("white"))
        main_sizer.Add(self.visualization_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.visualization_panel.Bind(wx.EVT_PAINT, self.OnPaintVisualization)
        self.planned_partitions_for_viz = [] # Data for visualization
        
        self.__MainPanel = MainPanel(self, wx.ID_ANY)
        main_sizer.Add(self.__MainPanel, 1, wx.EXPAND | wx.ALL, 4)

        self.SetSizer(main_sizer)

        self.Bind(wx.EVT_MENU, self.__MainPanel.on_show_all_drive, self.__menuItemShowAll) # Corrected binding
        self.Bind(wx.EVT_MENU, self.on_toggle_advanced_mode, self.menuItemAdvancedMode)
        self.Bind(wx.EVT_MENU, self.on_quit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_about, help_item)

        # Initialize multiboot panel but keep it hidden
        self.__MultibootPanel = MultibootPanel(self, wx.ID_ANY) # parent is self (MainFrame)
        main_sizer.Add(self.__MultibootPanel, 0, wx.EXPAND | wx.ALL, 5)
        self.__MultibootPanel.Hide()

        # Bind MainPanel's install button for state updates
        self.install_button_ref = self.__MainPanel.get_install_button()
        self.target_device_list_ref = self.__MainPanel.get_target_device_list()
        self.validate_options_and_set_install_button_state() # Initial state check


    def on_toggle_multiboot_mode(self, event):
        is_multiboot = self.cb_enable_multiboot.IsChecked()
        self.__MultibootPanel.Show(is_multiboot)
        self.__fs_panel.Show(not is_multiboot) # Hide standard filesystem picker if multiboot

        # Show/Hide MainPanel's source selection and advanced options based on multiboot mode
        self.__MainPanel.EnableLegacySourceSelection(not is_multiboot)

        # Also, the "Advanced Mode" from menu might conflict or be redundant with multiboot
        # For now, let's disable "Advanced Mode" menu item if Multiboot is on
        # and ensure its panel is hidden
        self.menuItemAdvancedMode.Enable(not is_multiboot)
        if is_multiboot:
            if self.menuItemAdvancedMode.IsChecked():
                self.menuItemAdvancedMode.Check(False)
            self.__MainPanel.ShowAdvancedOptions(False) # Hide if multiboot is on
        else:
            # Restore advanced options panel visibility based on menu item if not in multiboot
             self.__MainPanel.ShowAdvancedOptions(self.menuItemAdvancedMode.IsChecked())


        self.Layout()
        self.GetSizer().Fit(self) # Adjust frame size if needed
        self.validate_options_and_set_install_button_state()


    def validate_multiboot_options_and_set_install_button_state(self):
        # This function is called by MultibootPanel when its options change
        self.validate_options_and_set_install_button_state()

    def validate_options_and_set_install_button_state(self):
        # Central place to check all conditions and enable/disable install button
        if not self.install_button_ref: # Should not happen after init
            return

        target_selected = self.target_device_list_ref.GetSelection() != wx.NOT_FOUND

        if self.cb_enable_multiboot.IsChecked():
            # Multiboot mode validation
            can_install = target_selected and self.__MultibootPanel.is_valid()
        else:
            # Standard mode validation (from MainPanel.is_install_ok())
            can_install = target_selected and self.__MainPanel.is_legacy_install_ok()

        self.install_button_ref.Enable(can_install)


    def on_toggle_advanced_mode(self, event):
        # This is for the non-multiboot "Advanced Mode"
        if self.cb_enable_multiboot.IsChecked(): # Should not happen if menu item is disabled
            return
        is_advanced = self.menuItemAdvancedMode.IsChecked()
        self.__MainPanel.ShowAdvancedOptions(is_advanced)
        self.Layout() # Refresh layout

    def on_quit(self, __):
        self.Close(True)

    def on_about(self, __):
        my_dialog_about = DialogAbout(self, wx.ID_ANY)
        my_dialog_about.ShowModal()

    def is_show_all_checked(self):
        return self.__menuItemShowAll.IsChecked()

    def OnPaintVisualization(self, event):
        dc = wx.PaintDC(self.visualization_panel)
        dc.Clear() # Clear the panel

        panel_width, panel_height = self.visualization_panel.GetSize()

        if not self.planned_partitions_for_viz:
            # Get text extent to center it
            text = _("Partition layout preview will appear here when options are selected.")
            tw, th = dc.GetTextExtent(text)
            dc.DrawText(text, (panel_width - tw) // 2, (panel_height - th) // 2)
            return

        # --- This is conceptual drawing logic ---
        # Calculate total size for scaling (assuming 'size_bytes' is in the dict)
        try:
            total_disk_size_bytes = sum(part.get('size_bytes', 0) for part in self.planned_partitions_for_viz)
            if total_disk_size_bytes == 0: # Avoid division by zero if data is incomplete
                dc.DrawText("No partition sizes defined.", 5, 5)
                return
        except TypeError:
            dc.DrawText("Invalid partition data.", 5,5)
            return


        current_x = 2 # Start with a small margin
        padding = 2    # Padding between partitions

        for part in self.planned_partitions_for_viz:
            part_size_bytes = part.get('size_bytes', 0)
            part_width = int((part_size_bytes / total_disk_size_bytes) * (panel_width - (len(self.planned_partitions_for_viz) + 1) * padding) )
            part_width = max(part_width, 10) # Minimum width to be visible

            # Simple color coding (can be expanded)
            fs_type = part.get('fs', 'UNKNOWN').upper()
            if "ESP" in part.get('name', '').upper() or fs_type == "FAT16" or fs_type == "FAT32":
                color = wx.Colour("light grey")
            elif fs_type == "NTFS":
                color = wx.Colour("sky blue")
            elif fs_type == "EXFAT":
                color = wx.Colour("cyan")
            elif fs_type == "F2FS":
                color = wx.Colour("light green")
            elif fs_type == "LINUX-SWAP":
                color = wx.Colour("pink")
            else: # EXT4, BTRFS, etc.
                color = wx.Colour("orange")

            dc.SetBrush(wx.Brush(color))
            dc.SetPen(wx.Pen(wx.Colour("black"), 1)) # Border
            dc.DrawRectangle(current_x, 2, part_width, panel_height - 4)

            # Draw text label inside the partition
            label_text = f"{part.get('name', 'Part')}\n{part.get('fs', '')} ({utils.convert_to_human_readable_format(part_size_bytes)})"

            # Truncate text if too long for the box, or draw smaller
            # For simplicity, just draw it. Proper text fitting is more complex.
            # Check if text fits, otherwise just draw name
            text_width, text_height = dc.GetTextExtent(part.get('name', 'Part'))
            if text_width > part_width -4 :
                 label_text = part.get('name', 'P')[0:max(1,int(part_width/text_width*len(part.get('name', 'P')))-2)] + "..." if len(part.get('name', 'P')) > 1 else part.get('name', 'P')


            dc.SetFont(wx.Font(7, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            # Try to center text, very crudely
            # tw, th = dc.GetTextExtent(label_text.split('\n')[0]) # Just first line for now
            dc.DrawText(label_text, current_x + 3, 5)

            current_x += part_width + padding
        # --- End conceptual drawing logic ---

    def UpdateVisualizationDisplay(self, planned_layout_data):
        """
        Updates the data for the partition visualization and refreshes the panel.
        This function should be called after core logic planning functions are available
        and GUI event handlers can fetch the planned layout.

        :param planned_layout_data: A list of partition dictionaries.
                                   Each dict should have 'name', 'size_bytes', 'fs'.
        """
        self.planned_partitions_for_viz = planned_layout_data
        self.visualization_panel.Refresh() # Trigger OnPaintVisualization

    def get_selected_filesystem(self):
        """Get the filesystem type selected by the user"""
        selection = self.__filesystem_choice.GetSelection()
        if selection == 0:
            return "FAT"
        elif selection == 0:
            return "AUTO" # Auto Detect
        elif selection == 1:
            return "FAT32" # Changed from FAT
        elif selection == 2:
            return "NTFS"
        elif selection == 3:
            return "EXFAT"
        elif selection == 4:
            return "F2FS"
        elif selection == 5:
            return "BTRFS"
        return "AUTO"  # Default to AUTO if something goes wrong


class MultibootPanel(wx.Panel):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.TAB_TRAVERSAL):
        super(MultibootPanel, self).__init__(parent, ID, pos, size, style)
        self.parent_frame = parent # Reference to MainFrame to access things like __btInstall

        sizer = wx.StaticBoxSizer(wx.StaticBox(self, label=_("Multiboot Options")), wx.VERTICAL)

        # Filesystem for Payload/Data partition (used for Linux ISOs, Full Linux Install, general data)
        fs_payload_sizer = wx.BoxSizer(wx.HORIZONTAL)
        fs_payload_label = wx.StaticText(self, label=_("Payload Partition Filesystem:"))
        self.choice_payload_fs = wx.Choice(self, choices=[
            _("F2FS (Recommended for flash)"),
            _("exFAT (Good compatibility)"),
            _("NTFS (Windows native)"),
            _("BTRFS (Advanced features)")
            # FAT32 is not ideal for a large payload partition due to file size limits
        ])
        self.choice_payload_fs.SetSelection(0) # Default to F2FS
        fs_payload_sizer.Add(fs_payload_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        fs_payload_sizer.Add(self.choice_payload_fs, 1, wx.EXPAND)
        sizer.Add(fs_payload_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Windows-To-Go
        self.cb_wintogo = wx.CheckBox(self, label=_("Create Windows-To-Go"))
        # self.cb_wintogo.Enable(False) # Initially disabled, enabled by multiboot checkbox in MainFrame
        sizer.Add(self.cb_wintogo, 0, wx.ALL | wx.EXPAND, 5)

        # Windows ISO Picker (specific for WinToGo in Multiboot)
        win_iso_sizer = wx.BoxSizer(wx.HORIZONTAL)
        win_iso_label = wx.StaticText(self, label=_("Windows ISO (for WinToGo):"))
        self.file_picker_win_iso = wx.FilePickerCtrl(self, message=_("Select Windows ISO image"),
                                                    wildcard="ISO images (*.iso)|*.iso;*.ISO|All files|*")
        win_iso_sizer.Add(win_iso_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        win_iso_sizer.Add(self.file_picker_win_iso, 1, wx.EXPAND)
        sizer.Add(win_iso_sizer, 0, wx.EXPAND | wx.ALL, 5)


        # Linux ISOs Folder Picker
        linux_iso_dir_sizer = wx.BoxSizer(wx.HORIZONTAL)
        linux_iso_dir_label = wx.StaticText(self, label=_("Linux ISOs Folder (on USB):"))
        # Using TextCtrl for now, as DirPicker for a path *on the target USB* is conceptual until creation
        self.txt_linux_iso_dir = wx.TextCtrl(self, value="/boot/iso")
        linux_iso_dir_sizer.Add(linux_iso_dir_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        linux_iso_dir_sizer.Add(self.txt_linux_iso_dir, 1, wx.EXPAND)
        sizer.Add(linux_iso_dir_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Full Linux Install
        self.cb_full_linux_install = wx.CheckBox(self, label=_("Perform Full Linux Install"))
        sizer.Add(self.cb_full_linux_install, 0, wx.ALL | wx.EXPAND, 5)

        full_linux_sizer = wx.StaticBoxSizer(wx.StaticBox(self, label=_("Full Linux Install Details")), wx.VERTICAL)

        distro_sizer = wx.BoxSizer(wx.HORIZONTAL)
        distro_label = wx.StaticText(self, label=_("Distro for Install:"))
        self.choice_linux_distro = wx.Choice(self, choices=[
            _("Ubuntu"), _("Debian"), _("Arch Linux") # Add more as supported by backend
        ])
        distro_sizer.Add(distro_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        distro_sizer.Add(self.choice_linux_distro, 1, wx.EXPAND)
        full_linux_sizer.Add(distro_sizer, 0, wx.EXPAND | wx.ALL, 5)

        size_sizer = wx.BoxSizer(wx.HORIZONTAL)
        size_label = wx.StaticText(self, label=_("Size for Full Install (GiB):"))
        self.spin_linux_install_size = wx.SpinCtrl(self, min=10, max=1000, initial=20) # Sensible defaults
        size_sizer.Add(size_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        size_sizer.Add(self.spin_linux_install_size, 0, wx.RIGHT, 5) # Not expanding, fixed size
        full_linux_sizer.Add(size_sizer, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(full_linux_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Initially disable full linux install details
        self.choice_linux_distro.Enable(False)
        self.spin_linux_install_size.Enable(False)

        self.cb_full_linux_install.Bind(wx.EVT_CHECKBOX, self.on_toggle_full_linux_install)
        self.cb_wintogo.Bind(wx.EVT_CHECKBOX, self.on_multiboot_option_changed)
        self.file_picker_win_iso.Bind(wx.EVT_FILEPICKER_CHANGED, self.on_multiboot_option_changed)
        self.txt_linux_iso_dir.Bind(wx.EVT_TEXT, self.on_multiboot_option_changed)
        self.choice_payload_fs.Bind(wx.EVT_CHOICE, self.on_multiboot_option_changed)
        # Bindings for full linux install options will also call on_multiboot_option_changed
        self.choice_linux_distro.Bind(wx.EVT_CHOICE, self.on_multiboot_option_changed)
        self.spin_linux_install_size.Bind(wx.EVT_SPINCTRL, self.on_multiboot_option_changed)


        self.SetSizer(sizer)
        self.Layout()

    def on_toggle_full_linux_install(self, event):
        enabled = self.cb_full_linux_install.IsChecked()
        self.choice_linux_distro.Enable(enabled)
        self.spin_linux_install_size.Enable(enabled)
        self.on_multiboot_option_changed(event) # Trigger validation

    def on_multiboot_option_changed(self, event):
        # This method will be responsible for enabling/disabling the main "Install" button
        # based on the validity of multiboot options.
        # It needs access to the main install button, which is in MainPanel of MainFrame.
        # We'll call a method on the MainFrame to update the install button state.
        if self.parent_frame:
            self.parent_frame.validate_multiboot_options_and_set_install_button_state()


    def get_multiboot_options(self):
        opts = {
            "enabled": True, # Implied by this panel being active
            "payload_fs": self.choice_payload_fs.GetStringSelection().split(" ")[0].upper(),
            "wintogo_enabled": self.cb_wintogo.IsChecked(),
            "wintogo_iso_path": self.file_picker_win_iso.GetPath() if self.cb_wintogo.IsChecked() else None,
            "linux_iso_dir": self.txt_linux_iso_dir.GetValue(),
            "full_linux_install_enabled": self.cb_full_linux_install.IsChecked(),
            "full_linux_distro": self.choice_linux_distro.GetStringSelection() if self.cb_full_linux_install.IsChecked() else None,
            "full_linux_install_size_gib": self.spin_linux_install_size.GetValue() if self.cb_full_linux_install.IsChecked() else 0,
        }
        return opts

    def is_valid(self):
        # Basic validation for multiboot options
        if self.cb_wintogo.IsChecked() and not os.path.isfile(self.file_picker_win_iso.GetPath()):
            return False
        if not self.txt_linux_iso_dir.GetValue(): # Must not be empty
            return False
        if self.cb_full_linux_install.IsChecked():
            if self.choice_linux_distro.GetSelection() == wx.NOT_FOUND:
                return False
            if self.spin_linux_install_size.GetValue() <= 0: # Or some other minimum
                return False
        # Add other validation rules as needed
        return True


class MainPanel(wx.Panel):
    __parent = None

    __dvdDriveList = None
    __usbStickList = wx.ListBox

    __dvdDriveDevList = []
    __usbStickDevList = []

    __isoFile = wx.FilePickerCtrl

    __parentFrame = None

    __btInstall = None
    __btRefresh = None

    __isoChoice = None
    __dvdChoice = None

    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.TAB_TRAVERSAL):
        super(MainPanel, self).__init__(parent, ID, pos, size, style)

        self.__parent = parent

        # Controls
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Iso / CD
        main_sizer.Add(wx.StaticText(self, wx.ID_ANY, _("Source :")), 0, wx.ALL, 3)

        # Iso
        self.__isoChoice = wx.RadioButton(self, wx.ID_ANY, _("From a disk image (iso)"))
        main_sizer.Add(self.__isoChoice, 0, wx.ALL, 3)

        tmp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        tmp_sizer.AddSpacer(20)
        self.__isoFile = wx.FilePickerCtrl(self, wx.ID_ANY, "", _("Please select a disk image"),
                                       "Iso images (*.iso)|*.iso;*.ISO|All files|*")
        tmp_sizer.Add(self.__isoFile, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM, 3)
        main_sizer.Add(tmp_sizer, 0, wx.EXPAND, 0)

        # DVD
        self.__dvdChoice = wx.RadioButton(self, wx.ID_ANY, _("From a CD/DVD drive"))
        main_sizer.Add(self.__dvdChoice, 0, wx.ALL, 3)

        # List
        tmp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        tmp_sizer.AddSpacer(20)
        self.__dvdDriveList = wx.ListBox(self, wx.ID_ANY)
        tmp_sizer.Add(self.__dvdDriveList, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 3)
        main_sizer.Add(tmp_sizer, 1, wx.EXPAND, 0)

        # Target
        main_sizer.AddSpacer(20)

        main_sizer.Add(wx.StaticText(self, wx.ID_ANY, _("Target device :")), 0, wx.ALL, 3)

        # List
        self.__usbStickList = wx.ListBox(self, wx.ID_ANY)
        main_sizer.Add(self.__usbStickList, 1, wx.EXPAND | wx.ALL, 3)

        # Buttons
        main_sizer.AddSpacer(30)

        bt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.__btRefresh = wx.Button(self, wx.ID_REFRESH)
        bt_sizer.Add(self.__btRefresh, 0, wx.ALL, 3)
        self.__btInstall = wx.Button(self, wx.ID_ANY, _("Install"))
        bt_sizer.Add(self.__btInstall, 0, wx.ALL, 3)

        main_sizer.Add(bt_sizer, 0, wx.ALIGN_RIGHT, 0)

        # Finalization
        self.SetSizer(main_sizer)

        self.Bind(wx.EVT_LISTBOX, self.on_list_or_file_modified, self.__usbStickList)
        self.Bind(wx.EVT_LISTBOX, self.on_list_or_file_modified, self.__dvdDriveList)
        self.Bind(wx.EVT_FILEPICKER_CHANGED, self.on_list_or_file_modified, self.__isoFile)

        self.Bind(wx.EVT_BUTTON, self.on_install, self.__btInstall)
        self.Bind(wx.EVT_BUTTON, self.on_refresh, self.__btRefresh)

        self.Bind(wx.EVT_RADIOBUTTON, self.on_source_option_changed, self.__isoChoice)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_source_option_changed, self.__dvdChoice)

        self.refresh_list_content()
        self.on_source_option_changed(wx.CommandEvent)
        self.__btInstall.Enable(self.is_legacy_install_ok()) # Changed from is_install_ok

        # Advanced Options Panel (initially hidden)
        self.advanced_options_panel = AdvancedOptionsPanel(self, wx.ID_ANY)
        main_sizer.Add(self.advanced_options_panel, 0, wx.EXPAND | wx.ALL, 5)
        self.advanced_options_panel.Hide() # Start hidden

        # Bind the install button to the MainFrame's on_install handler
        self.__btInstall.Bind(wx.EVT_BUTTON, self.GetParent().on_install_clicked)


    def ShowAdvancedOptions(self, show):
        self.advanced_options_panel.Show(show)
        self.Layout()

    def refresh_list_content(self):
        # USB
        self.__usbStickDevList = []
        self.__usbStickList.Clear()

        # Ensure parent frame reference for is_show_all_checked and validation call
        parent_frame = self.GetParent() # MainFrame instance
        if not parent_frame: return


        show_all_checked = parent_frame.is_show_all_checked()

        device_list = list_devices.usb_drive(show_all_checked)

        for device in device_list:
            self.__usbStickDevList.append(device[0])
            self.__usbStickList.Append(device[1])

        # ISO
        self.__dvdDriveDevList = []
        self.__dvdDriveList.Clear()

        drive_list = list_devices.dvd_drive()

        for drive in drive_list:
            self.__dvdDriveDevList.append(drive[0])
            self.__dvdDriveList.Append(drive[1])

        parent_frame.validate_options_and_set_install_button_state()


    # is_legacy_install_ok, on_source_option_changed, on_list_or_file_modified, on_refresh
    # have already been updated to call GetParent().validate_options_and_set_install_button_state()

    # The original on_install is being moved/refactored into MainFrame.
    # MainPanel will now have methods to get the selected options for either mode.

    def get_legacy_options(self):
        if not self.is_legacy_install_ok():
            return None # Should not happen if button is correctly disabled

        device = self.__usbStickDevList[self.__usbStickList.GetSelection()]
        is_iso = self.__isoChoice.GetValue()
        source_media = self.__isoFile.GetPath() if is_iso else self.__dvdDriveDevList[self.__dvdDriveList.GetSelection()]

        # Get parent frame (MainFrame) to access options like filesystem, boot_flag, skip_grub
        parent_frame = self.GetParent()
        filesystem = parent_frame.get_selected_filesystem() # This needs to exist in MainFrame
        boot_flag = parent_frame.options_boot.IsChecked()
        skip_grub = parent_frame.options_skip_grub.IsChecked()

        return {
            "source_media": source_media,
            "target_device": device,
            "filesystem": filesystem,
            "boot_flag": boot_flag,
            "skip_grub": skip_grub
        }

    def on_show_all_drive(self, __):
        self.refresh_list_content()
        # Call validation on MainFrame after refreshing lists
        parent_frame = self.GetParent()
        if parent_frame:
            parent_frame.validate_options_and_set_install_button_state()

# Add to MainFrame class:
    def get_selected_filesystem(self): # Moved from MainPanel, now in MainFrame
        # This is for the standard mode filesystem picker
        selection = self.__filesystem_choice.GetSelection()
        if selection == 0: return "AUTO"
        elif selection == 1: return "FAT32"
        elif selection == 2: return "NTFS"
        elif selection == 3: return "EXFAT"
        elif selection == 4: return "F2FS"
        elif selection == 5: return "BTRFS"
        return "AUTO"

    def on_install_clicked(self, event):
        # Confirmation Dialog
        if wx.MessageBox(
            _("Are you sure? This will delete all data on the selected target device."),
            _("Confirm Action"), # Changed title for clarity
            wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT, # Changed icon and default
            self) != wx.YES:
            return

        target_device_path = self.__MainPanel.get_target_device_list_path() # Needs to be implemented in MainPanel
        if not target_device_path:
             wx.MessageBox(_("No target device selected or device path not found."), _("Error"), wx.OK | wx.ICON_ERROR, self)
             return


        if self.cb_enable_multiboot.IsChecked():
            # MULTIBOOT MODE
            multiboot_opts = self.__MultibootPanel.get_multiboot_options()

            # Prepare os_configs for create_multiboot_usb backend
            os_configs = []
            if multiboot_opts["wintogo_enabled"]:
                if not multiboot_opts["wintogo_iso_path"] or not os.path.isfile(multiboot_opts["wintogo_iso_path"]):
                    wx.MessageBox(_("Windows ISO for WinToGo is not valid or not selected."), _("Error"), wx.OK | wx.ICON_ERROR, self)
                    return
                os_configs.append({
                    "type": "windows",
                    "name": "Windows-To-Go", # Or make this configurable
                    "iso_path": multiboot_opts["wintogo_iso_path"],
                    # Size for WinToGo partition will be handled by backend partitioning strategy,
                    # for now, it implies a dedicated partition based on --win-size-gb if that was a CLI opt.
                    # The GUI doesn't have a specific size for WinToGo partition itself, it's part of the layout.
                    # We might need a default or a way to specify this if the backend requires it explicitly here.
                    # For now, assuming backend `create_multiboot_usb` handles this partitioning.
                    "filesystem": "NTFS", # Typically NTFS for Windows
                    "wintogo": True
                })

            # Placeholder for how Linux ISOs are handled. The backend `create_multiboot_usb`
            # currently takes a list of ISOs. The GUI has a *folder*.
            # This part needs reconciliation with backend. For now, this is conceptual.
            # If `main_multiboot` or a similar new function is used, it might take the folder directly.
            # For now, we assume `create_multiboot_usb` or its GUI counterpart will handle the ISO dir.

            # Full Linux Install config
            if multiboot_opts["full_linux_install_enabled"]:
                 os_configs.append({
                    "type": "linux_full_install", # A distinct type for the backend
                    "name": f"Full {multiboot_opts['full_linux_distro']} Install",
                    "distro": multiboot_opts['full_linux_distro'].lower(), # e.g., "ubuntu"
                    # Release might be needed for debootstrap/pacstrap, not currently in GUI
                    "size_mb": multiboot_opts['full_linux_install_size_gib'] * 1024,
                    "filesystem": multiboot_opts['payload_fs'], # Full install goes on payload fs
                 })


            # TODO: Wire up the actual call to the multiboot backend function.
            # This will likely involve a new Multiboot_handler thread similar to WowUSB_handler.
            # For now, simulate with a message.

            # Example of parameters for a potential backend call:
            # backend_params = {
            #     "target_device": target_device_path,
            #     "os_configs": os_configs, # This needs to be built carefully
            #     "linux_iso_dir": multiboot_opts["linux_iso_dir"], # Pass this to backend
            #     "shared_filesystem": multiboot_opts["payload_fs"], # Payload FS is the main "shared" or "data" area
            #     # shared_size_mb might be 'remaining space' or configured in backend based on other partitions
            #     "verbose": True # Or from a GUI option
            # }

            # For now, using a placeholder for the handler and call
            mb_handler = Multiboot_handler(
                target_device=target_device_path,
                wintogo_iso=multiboot_opts["wintogo_iso_path"] if multiboot_opts["wintogo_enabled"] else None,
                linux_iso_dir=multiboot_opts["linux_iso_dir"],
                payload_fs=multiboot_opts["payload_fs"],
                full_linux_distro=multiboot_opts["full_linux_distro"].lower() if multiboot_opts["full_linux_install_enabled"] else None,
                full_linux_size_gb=multiboot_opts["full_linux_install_size_gib"] if multiboot_opts["full_linux_install_enabled"] else None
                # More params as needed by the actual backend call
            )
            self.run_handler_with_progress(mb_handler, _("Creating Multiboot USB..."))


        else:
            # LEGACY (SINGLE BOOT) MODE
            legacy_opts = self.__MainPanel.get_legacy_options()
            if not legacy_opts: # Should be caught by button state, but good practice
                wx.MessageBox(_("Legacy options are not correctly configured."), _("Error"), wx.OK | wx.ICON_ERROR, self)
                return

            legacy_handler = WowUSB_handler(
                source=legacy_opts["source_media"],
                target=target_device_path, # Using the path obtained earlier
                boot_flag=legacy_opts["boot_flag"],
                filesystem=legacy_opts["filesystem"],
                skip_grub=legacy_opts["skip_grub"]
            )
            self.run_handler_with_progress(legacy_handler, _("Installing Windows (Legacy)..."))

    def run_handler_with_progress(self, handler_instance, progress_title):
        handler_instance.start()
        dialog = wx.ProgressDialog(progress_title, _("Please wait..."), 101, self,
                                   wx.PD_APP_MODAL | wx.PD_SMOOTH | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME | wx.PD_REMAINING_TIME)

        log_output_ctrl = None # Placeholder for future log pane integration
        # Example: if self.log_pane_exists: log_output_ctrl = self.my_log_text_ctrl

        while handler_instance.is_alive():
            # Update log pane if available
            # new_log_messages = handler_instance.get_pending_log_messages() # Handler needs this method
            # if log_output_ctrl and new_log_messages:
            #    log_output_ctrl.AppendText("".join(new_log_messages))

            if not handler_instance.progress: # Using Pulse for indeterminate stages
                status = dialog.Pulse(handler_instance.state)[0]
                time.sleep(0.1) # Pulse can be CPU intensive, short sleep
            else: # Using Update for determinate progress
                status = dialog.Update(handler_instance.progress, handler_instance.state)[0]

            wx.GetApp().Yield() # Keep UI responsive

            if not status: # Cancel button pressed
                if wx.MessageBox(_("Are you sure you want to cancel the operation?"), _("Confirm Cancel"),
                                  wx.YES_NO | wx.ICON_QUESTION, self) == wx.YES:
                    handler_instance.kill = True # Signal thread to stop
                    # handler_instance.join(timeout=5) # Wait briefly for thread to try and clean up
                    break
                else:
                    dialog.Resume() # Resume progress dialog if user chose not to cancel

        # Ensure dialog is destroyed even if loop exited early due to completion
        if dialog:
            dialog.Destroy()

        if handler_instance.error:
            wx.MessageBox(_("Operation failed!") + "\n" + str(handler_instance.error),
                          _("Operation Status"), wx.OK | wx.ICON_ERROR, self)
        elif not handler_instance.kill: # If not cancelled
            wx.MessageBox(_("Operation completed successfully!"),
                          _("Operation Status"), wx.OK | wx.ICON_INFORMATION, self)
        else: # Was cancelled
             wx.MessageBox(_("Operation cancelled by user."),
                          _("Operation Status"), wx.OK | wx.ICON_INFORMATION, self)


# Need to add get_target_device_list_path() to MainPanel
class MainPanel(wx.Panel):
    # ... (existing MainPanel code) ...
    def get_target_device_list_path(self):
        selection = self.__usbStickList.GetSelection()
        if selection != wx.NOT_FOUND and self.__usbStickDevList:
            return self.__usbStickDevList[selection]
        return None

# New Multiboot_handler class (basic shell, needs to call backend)
# This is a simplified version. The actual backend call and progress reporting
# will depend on the `main_multiboot` or `create_multiboot_usb` function's design.
class Multiboot_handler(threading.Thread):
    progress = 0 # Can be percentage or False for indeterminate
    state = ""
    error = ""
    kill = False
    # log_messages_lock = threading.Lock() # For thread-safe log message collection
    # pending_log_messages = [] # Store messages here

    def __init__(self, target_device, wintogo_iso, linux_iso_dir, payload_fs,
                 full_linux_distro, full_linux_size_gb, **kwargs):
        threading.Thread.__init__(self)
        self.target_device = target_device
        self.wintogo_iso = wintogo_iso
        self.linux_iso_dir = linux_iso_dir
        self.payload_fs = payload_fs
        self.full_linux_distro = full_linux_distro
        self.full_linux_size_gb = full_linux_size_gb
        self.kwargs = kwargs # For other potential params

        # Link to core.gui for progress updates is not standard for non-legacy.
        # Instead, this handler should update its own `progress` and `state` attributes.
        # The GUI will poll these.
        # If direct logging from backend is needed, a queue or callback mechanism is better.
        # For now, we assume the backend `main_multiboot` (or equivalent) will print to stdout/stderr
        # and this handler might try to capture it or the backend is modified to report progress.

    # def log_message(self, message): # Example method for backend to call
    #    with self.log_messages_lock:
    #        self.pending_log_messages.append(message + "\n")

    # def get_pending_log_messages(self):
    #    with self.log_messages_lock:
    #        messages = list(self.pending_log_messages)
    #        self.pending_log_messages.clear()
    #        return messages

    def run(self):
        self.state = _("Initializing multiboot creation...")
        self.progress = False # Indeterminate start

        # This is where the call to the actual multiboot creation logic from `WowUSB/multiboot.py` would go.
        # e.g., from WowUSB.multiboot import main_multiboot_cli_entry as main_multiboot_backend
        # Or: from WowUSB import multiboot (if main_multiboot is directly usable)

        # Construct arguments for the backend. This is highly dependent on how
        # `main_multiboot` (or a new GUI-specific function in `multiboot.py`) is structured.
        # For demonstration, let's assume a function `run_multiboot_creation` exists.

        # Simplified CLI arguments construction for a hypothetical backend
        cli_args = ["--target", self.target_device]
        if self.wintogo_iso:
            cli_args.extend(["--win-iso", self.wintogo_iso])
            # The GUI doesn't have a separate wintogo_size, it's part of layout.
            # Backend needs to handle this, or GUI needs a field.
            # Assuming a default or smart calculation in backend for now.
            # cli_args.extend(["--win-size-gb", "64"]) # Example default if needed

        if self.linux_iso_dir: # This is a directory, backend needs to handle scanning it.
            # The CLI for multiboot.py takes multiple --linux-iso flags.
            # The GUI gives a directory. This implies the backend (`main_multiboot` or a wrapper)
            # needs to be adapted to take `--linux-iso-dir` or scan the dir itself.
            # For now, assuming the backend will be enhanced or we use a placeholder.
            # This is a key area for backend integration.
            # Let's assume a new backend parameter --linux-iso-dir is added.
            cli_args.extend(["--linux-iso-dir", self.linux_iso_dir])


        if self.full_linux_distro:
            cli_args.extend(["--full-linux-install", self.full_linux_distro])
            cli_args.extend(["--full-linux-size-gb", str(self.full_linux_size_gb)])
            # Release codename for full linux install is not in GUI, backend might need a default or error out.

        cli_args.extend(["--payload-fs", self.payload_fs])
        # cli_args.append("--verbose") # If a verbose option is available

        try:
            self.state = _("Preparing partitions...")
            # Simulate some work
            for i in range(5):
                if self.kill: raise SystemExit("Operation cancelled by user via GUI")
                time.sleep(0.5)
                self.progress = (i + 1) * 5 # 0 to 25%
                self.state = _("Partitioning... {}%").format(self.progress)

            # Placeholder for actual call:
            # Option 1: Call a function directly (preferred for GUI integration)
            # import WowUSB.multiboot
            # result_code = WowUSB.multiboot.main_multiboot(
            # target_device=self.target_device,
            # wintogo_iso=self.wintogo_iso,
            # linux_iso_dir=self.linux_iso_dir, # Needs backend support for dir
            # payload_fs=self.payload_fs,
            # full_linux_install_distro=self.full_linux_distro,
            # full_linux_install_size_gb=self.full_linux_size_gb,
            # progress_callback=self.update_progress_from_backend # Backend needs to support this
            # )
            # if result_code != 0: self.error = "Multiboot creation failed (see logs)"

            # Option 2: Run as subprocess (less ideal for progress, but uses existing CLI entry)
            # This assumes `WowUSB/wowusb` is the CLI entry point and can call multiboot.
            # Or, if `multiboot.py` is directly executable with these args.
            # cmd = ["python3", "-m", "WowUSB.multiboot"] + cli_args # Example
            # process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            # while True:
            #     if self.kill: process.terminate(); break
            #     line = process.stdout.readline()
            #     if not line: break
            #     self.log_message(line.strip()) # Send to log pane
            #     # Parse line for progress if backend outputs it in a structured way
            # process.wait()
            # if process.returncode != 0: self.error = "Multiboot script failed."

            # --- SIMULATING THE REST OF THE PROCESS ---
            self.state = _("Copying Windows files (if selected)...")
            self.progress = 30
            for i in range(10):
                if self.kill: raise SystemExit("Operation cancelled by user via GUI")
                time.sleep(0.5)
                self.progress = 30 + (i + 1) * 2 # 30 to 50%
                self.state = _("Copying Windows... {}%").format(self.progress)

            self.state = _("Setting up Linux ISOs...")
            self.progress = 55
            for i in range(10):
                if self.kill: raise SystemExit("Operation cancelled by user via GUI")
                time.sleep(0.3)
                self.progress = 55 + (i + 1) * 1.5 # 55 to 70%
                self.state = _("Processing Linux ISOs... {}%").format(int(self.progress))

            if self.full_linux_distro:
                self.state = _("Performing full Linux install ({distro})...").format(distro=self.full_linux_distro)
                self.progress = 75
                for i in range(10):
                    if self.kill: raise SystemExit("Operation cancelled by user via GUI")
                    time.sleep(1) # Full install can be long
                    self.progress = 75 + (i + 1) * 2 # 75 to 95%
                    self.state = _("Installing {distro}... {p}%").format(distro=self.full_linux_distro, p=int(self.progress))

            self.state = _("Installing GRUB bootloader...")
            self.progress = 98
            time.sleep(2)
            if self.kill: raise SystemExit("Operation cancelled by user via GUI")

            self.state = _("Finalizing...")
            self.progress = 100
            time.sleep(1)
            # --- END SIMULATION ---

        except SystemExit as e:
            if "Operation cancelled by user via GUI" in str(e):
                self.error = _("Operation Cancelled.")
            else:
                self.error = _("Operation exited: {}").format(str(e))
        except Exception as e:
            self.error = str(e)
            # import traceback # For debugging
            # self.error += "\n" + traceback.format_exc()
        finally:
            # Cleanup if necessary
            pass

    # def update_progress_from_backend(self, progress_percent, message):
    #    if self.kill: raise SystemExit("Operation cancelled by user via GUI") # Allow backend to stop
    #    self.progress = progress_percent
    #    self.state = message
    #    # self.log_message(message)


# Modify WowUSB_handler to also use the new progress update mechanism if desired,
# or keep its own if core.gui linkage is preferred for legacy.
# For consistency, it's better if both handlers update self.progress and self.state.
# The core.main function would need to be adapted or WowUSB_handler changes how it gets progress.

# Quick adaptation for WowUSB_handler (conceptual, core.py would need changes)
class WowUSB_handler(threading.Thread):
    progress = 0 # Use 0-100, or False for indeterminate
    state = ""
    error = ""
    kill = False
    # log_messages_lock = threading.Lock()
    # pending_log_messages = []

    def __init__(self, source, target, boot_flag, filesystem, skip_grub=False):
        threading.Thread.__init__(self)
        # core.gui = self # This direct linkage is problematic for multiple handler types / clean MVC
        self.source = source
        self.target = target
        self.boot_flag = boot_flag
        self.filesystem = filesystem
        self.skip_grub = skip_grub

        # We need a way for core.main to report progress back to *this instance*
        # Option A: Pass `self` (this handler instance) to core.init/main,
        #           and core.main calls methods like self.update_progress(percent, message)
        # Option B: core.main uses a global or passed-in queue that this handler reads from.
        # For now, we'll assume core.py is modified for Option A.
        # WowUSB.core.progress_reporter = self # Example of how core.py might get a ref

    # def update_progress(self, percent, message): # Called by core.main
    #    if self.kill: raise SystemExit("Operation cancelled by user via GUI")
    #    self.progress = percent
    #    self.state = message
    #    # self.log_message(message)

    # def log_message(self, message): # (same as in Multiboot_handler)
    #    with self.log_messages_lock:
    #        self.pending_log_messages.append(message + "\n")

    # def get_pending_log_messages(self): # (same as in Multiboot_handler)
    #    with self.log_messages_lock:
    #        messages = list(self.pending_log_messages)
    #        self.pending_log_messages.clear()
    #        return messages

    def run(self):
        # Unset the global core.gui if it was used, to avoid interference
        # if hasattr(core, 'gui') and core.gui is self:
        #    core.gui = None

        # Set up a progress callback for the core functions
        # This requires core.init and core.main to accept a progress_callback argument
        def progress_callback_for_core(phase, percent, message):
            if self.kill:
                # This needs to be an exception that core.main can catch and stop cleanly
                raise OperationCancelledError("Operation cancelled by user via GUI")
            self.state = f"[{phase}] {message}"
            self.progress = percent if percent is not None else False # False for indeterminate pulse

        try:
            # Pass `progress_callback_for_core` to core functions.
            # This is a significant change to core.py's interface.
            # For now, we will *not* assume core.py is changed yet, and the old
            # core.gui mechanism might still be active if not refactored.
            # The progress dialog will rely on self.progress and self.state being updated.
            # If core.gui = self is still used by core.py, it will update this thread's attributes.

            # To make the new progress dialog work with existing WowUSB_handler that uses core.gui:
            # We assume core.py's use of core.gui.progress and core.gui.state will update this thread's
            # self.progress and self.state because core.gui was set to self.
            # This is a bit of a hack but avoids immediate core.py changes.
            original_core_gui = getattr(core, 'gui', None)
            core.gui = self # Temporarily set for this operation

            source_fs_mountpoint, target_fs_mountpoint, temp_directory, target_media = core.init(
                from_cli=False,
                install_mode="device", # Or "partition" if that mode is ever used by GUI
                source_media=self.source,
                target_media=self.target
                # progress_callback=progress_callback_for_core # Ideal future change
            )
            core.main(source_fs_mountpoint, target_fs_mountpoint, self.source, self.target, "device", temp_directory,
                    self.filesystem, self.boot_flag, None, self.skip_grub
                    # progress_callback=progress_callback_for_core # Ideal future change
                    )
        except SystemExit as e:
            if "Operation cancelled by user via GUI" in str(e):
                self.error = _("Operation Cancelled.")
            elif "Operation exited." in str(e) : # From original gui.py
                 self.error = _("Operation exited.")
            else: # Some other SystemExit
                self.error = _("Operation failed: {}").format(str(e))
        except Exception as e:
            self.error = str(e)
            # import traceback # For debugging
            # if core.debug: self.error += "\n" + traceback.format_exc()
        finally:
            # Ensure cleanup is always called
            core.cleanup(source_fs_mountpoint, target_fs_mountpoint, temp_directory, target_media)
            core.gui = original_core_gui # Restore original core.gui state


class DialogAbout(wx.Dialog):
    __bitmapIcone = None
    __staticTextTitre = None
    __staticTextVersion = None
    __NotebookAutorLicence = None
    __MyPanelNoteBookAutors = None
    __BtOk = None

    def __init__(self, parent, ID=wx.ID_ANY, title=_("About"), pos=wx.DefaultPosition, size=wx.Size(650, 590),
                 style=wx.DEFAULT_DIALOG_STYLE):
        super(DialogAbout, self).__init__(parent, ID, title, pos, size, style)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        sizer_all = wx.BoxSizer(wx.VERTICAL)
        sizer_img = wx.BoxSizer(wx.HORIZONTAL)

        img = wx.Image(data_directory + "icon.ico", wx.BITMAP_TYPE_ICO).Scale(48, 48, wx.IMAGE_QUALITY_BILINEAR)
        self.__bitmapIcone = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(img), wx.DefaultPosition, wx.Size(48, 48))
        sizer_img.Add(self.__bitmapIcone, 0, wx.ALL, 5)

        sizer_text = wx.BoxSizer(wx.VERTICAL)

        self.__staticTextTitre = wx.StaticText(self, wx.ID_ANY, "WowUSB-DS9")
        self.__staticTextTitre.SetFont(wx.Font(16, 74, 90, 92, False, "Sans"))
        self.__staticTextTitre.SetForegroundColour(wx.Colour(0, 60, 118))
        sizer_text.Add(self.__staticTextTitre, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        self.__staticTextVersion = wx.StaticText(self, wx.ID_ANY, miscellaneous.__version__)
        self.__staticTextVersion.SetFont(wx.Font(10, 74, 90, 92, False, "Sans"))
        self.__staticTextVersion.SetForegroundColour(wx.Colour(69, 141, 196))
        sizer_text.Add(self.__staticTextVersion, 0, wx.LEFT, 5)
        sizer_img.Add(sizer_text, 0, 0, 5)
        sizer_all.Add(sizer_img, 0, wx.EXPAND, 5)

        self.__NotebookAutorLicence = wx.Notebook(self, wx.ID_ANY)

        self.__NotebookAutorLicence.AddPage(
            PanelNoteBookAutors(self.__NotebookAutorLicence, wx.ID_ANY, "slacka \nLin-Buo-Ren\nWaxyMocha", data_directory + "woeusb-logo.png",
                             "github.com/rebots-online/WowUSB"), _("Authors"), True)
        self.__NotebookAutorLicence.AddPage(
            PanelNoteBookAutors(self.__NotebookAutorLicence, wx.ID_ANY, "Colin GILLE / Congelli501",
                             data_directory + "c501-logo.png", "www.congelli.eu"), _("Original WinUSB Developer"), False)

        licence_str = _('''
            This file is part of WowUSB-DS9.

            WowUSB-DS9 is free software: you can redistribute it and/or modify
            it under the terms of the GNU General Public License as published by
            the Free Software Foundation, either version 3 of the License, or
            (at your option) any later version.

            WowUSB-DS9 is distributed in the hope that it will be useful,
            but WITHOUT ANY WARRANTY; without even the implied warranty of
            MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
            GNU General Public License for more details.

            You should have received a copy of the GNU General Public License
            along with WowUSB-DS9.  If not, see <http://www.gnu.org/licenses/>.
        ''')

        licence_txt = wx.TextCtrl(self.__NotebookAutorLicence, wx.ID_ANY, licence_str, wx.DefaultPosition,
                               wx.DefaultSize, wx.TE_MULTILINE | wx.TE_READONLY)

        self.__NotebookAutorLicence.AddPage(licence_txt, _("License"))

        sizer_all.Add(self.__NotebookAutorLicence, 1, wx.EXPAND | wx.ALL, 5)

        self.__BtOk = wx.Button(self, wx.ID_OK)
        sizer_all.Add(self.__BtOk, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 5)
        self.__BtOk.SetFocus()

        self.SetSizer(sizer_all)
        self.Layout()

class AdvancedOptionsPanel(wx.Panel):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.TAB_TRAVERSAL):
        super(AdvancedOptionsPanel, self).__init__(parent, ID, pos, size, style)

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Example advanced option (more would be added here)
        self.cb_force_gpt = wx.CheckBox(self, label=_("Force GPT partition table"))
        lbl_info = wx.StaticText(self, label=_("More advanced options will appear here (e.g., custom GRUB, cluster size)."))

        sizer.Add(self.cb_force_gpt, 0, wx.ALL, 5)
        sizer.Add(lbl_info, 0, wx.ALL, 5)

        self.SetSizer(sizer)
        self.Layout()

    def GetAdvancedOptions(self):
        """
        Returns a dictionary of selected advanced options.
        Example: {'force_gpt': True}
        """
        return {
            'force_gpt': self.cb_force_gpt.IsChecked(),
            # Add other options here
        }

class MainPanel(wx.Panel): # Existing MainPanel class, adding methods
    # ... (other __init__ parts remain the same) ...
    # Add these new methods to MainPanel:

    def get_install_button(self):
        return self.__btInstall

    def get_target_device_list(self):
        return self.__usbStickList

    def EnableLegacySourceSelection(self, enable):
        # This method will enable/disable the ISO/DVD source part of the MainPanel
        self.__isoChoice.Enable(enable)
        self.__dvdChoice.Enable(enable)

        # Only enable file picker or DVD list if their respective radio button is selected AND master enable is true
        if enable:
            self.__isoFile.Enable(self.__isoChoice.GetValue())
            self.__dvdDriveList.Enable(self.__dvdChoice.GetValue())
        else:
            self.__isoFile.Enable(False)
            self.__dvdDriveList.Enable(False)

        # Also update the install button state as source availability changes
        self.GetParent().validate_options_and_set_install_button_state()


    def is_legacy_install_ok(self):
        # Renamed from is_install_ok to avoid confusion with overall validation
        # This checks conditions for *non-multiboot* (legacy) mode
        source_ok = (self.__isoChoice.GetValue() and os.path.isfile(self.__isoFile.GetPath())) or \
                    (self.__dvdChoice.GetValue() and self.__dvdDriveList.GetSelection() != wx.NOT_FOUND)
        target_ok = self.__usbStickList.GetSelection() != wx.NOT_FOUND
        return source_ok and target_ok

    # Modify on_source_option_changed and on_list_or_file_modified
    # to call the new central validation method in MainFrame.
    def on_source_option_changed(self, __):
        is_iso = self.__isoChoice.GetValue()
        self.__isoFile.Enable(is_iso)
        self.__dvdDriveList.Enable(not is_iso)
        self.GetParent().validate_options_and_set_install_button_state()


    def on_list_or_file_modified(self, event):
        if event.GetEventType() == wx.EVT_LISTBOX.typeId and not event.IsSelection(): # EVT_LISTBOX.typeId for older wx
             return
        self.GetParent().validate_options_and_set_install_button_state()

    # Ensure on_refresh also calls the validation
    def on_refresh(self, __):
        self.refresh_list_content() # This already calls __btInstall.Enable via is_install_ok
                                    # We should change that to call the MainFrame validation
        self.GetParent().validate_options_and_set_install_button_state()


    # The on_install method needs to be significantly refactored
    # to handle both legacy and multiboot modes.
    # This will be a larger change, done in a subsequent step.
    # For now, ensure the original on_install logic calls the MainFrame validation before proceeding.
    # def on_install(self, __): ... will be updated later ...


class PanelNoteBookAutors(wx.Panel):
    def __init__(self, parent, ID=wx.ID_ANY, autherName="", imgName="", siteLink="", pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.TAB_TRAVERSAL):
        super(PanelNoteBookAutors, self).__init__(parent, ID, pos, size, style)

        sizer_note_book_autors = wx.BoxSizer(wx.VERTICAL)

        auteur_static_text = wx.StaticText(self, wx.ID_ANY, autherName)
        sizer_note_book_autors.Add(auteur_static_text, 0, wx.ALL, 5)

        if siteLink != "":
            autor_link = wx.adv.HyperlinkCtrl(self, wx.ID_ANY, siteLink, siteLink)
            sizer_note_book_autors.Add(autor_link, 0, wx.LEFT | wx.BOTTOM, 5)

        if imgName != "":
            img = wx.Image(imgName, wx.BITMAP_TYPE_PNG)
            img_autor_logo = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(img))
            sizer_note_book_autors.Add(img_autor_logo, 0, wx.LEFT, 5)

        self.SetSizer(sizer_note_book_autors)


class WowUSB_handler(threading.Thread):
    """
    Class for handling communication with woeusb.
    """
    progress = False
    state = ""
    error = ""
    kill = False

    def __init__(self, source, target, boot_flag, filesystem, skip_grub=False):
        threading.Thread.__init__(self)

        core.gui = self
        self.source = source
        self.target = target
        self.boot_flag = boot_flag
        self.filesystem = filesystem
        self.skip_grub = skip_grub

    def run(self):
        source_fs_mountpoint, target_fs_mountpoint, temp_directory, target_media = core.init(
            from_cli=False,
            install_mode="device",
            source_media=self.source,
            target_media=self.target
        )
        try:
            core.main(source_fs_mountpoint, target_fs_mountpoint, self.source, self.target, "device", temp_directory,
                    self.filesystem, self.boot_flag, None, self.skip_grub)
        except SystemExit as e: # Catch SystemExit, which OperationCancelledError inherits from
            if "Operation cancelled by user via GUI" in str(e):
                self.error = _("Operation Cancelled.")
                # self.progress is already likely False or some value, dialog will stop
            else:
                # Some other SystemExit, perhaps from core.py doing its own sys.exit()
                # This path might need more refinement depending on how core.py exits.
                self.error = _("Operation exited.")
            # No need to print traceback for user-initiated cancel or clean SystemExit
        except Exception as e:
            self.error = str(e)
            if core.debug: # Assuming core.debug is set appropriately
                self.error += "\n" + traceback.format_exc()
        finally:
            # Ensure cleanup is always called
            core.cleanup(source_fs_mountpoint, target_fs_mountpoint, temp_directory, target_media)


def run():
    frameTitle = "WowUSB-DS9"

    frame = MainFrame(frameTitle, wx.DefaultPosition, wx.Size(400, 600))
    frame.SetMinSize(wx.Size(300, 450))

    frame.Show(True)
    app.MainLoop()


def main():
    run()

if __name__ == "__main__":
    run()

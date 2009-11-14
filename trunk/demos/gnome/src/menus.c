/* menus.c
 *
 * Copyright (C) 1999 Havoc Pennington
 *
 * This program is free software; you can redistribute it and/or 
 * modify it under the terms of the GNU General Public License as 
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
 * USA
 */

#include <config.h>
#include <glib/gi18n.h>
#include <stdlib.h>

#include "menus.h"
#include "app.h"

static void nothing_action_callback (GtkAction* action, gpointer data);
static void new_action_callback     (GtkAction* action, gpointer data);
static void close_action_callback   (GtkAction* action, gpointer data);
static void quit_action_callback    (GtkAction* action, gpointer data);
static void about_action_callback   (GtkAction* action, gpointer data);

static const gchar *ui =
  "<ui>"
  "  <menubar>"
  "    <menu action='file'>"
  "      <menuitem action='new'/>"
  "      <menuitem action='open'/>"
  "      <menuitem action='save'/>"
  "      <menuitem action='save-as'/>"
  "      <separator/>"
  "      <menuitem action='close'/>"
  "      <menuitem action='quit'/>"
  "    </menu>"
  "    <menu action='edit'>"
  "      <menuitem action='cut'/>"
  "      <menuitem action='copy'/>"
  "      <menuitem action='paste'/>"
  "      <menuitem action='select-all'/>"
  "      <menuitem action='clear'/>"
  "      <separator/>"
  "      <menuitem action='undo'/>"
  "      <menuitem action='redo'/>"
  "      <separator/>"
  "      <menuitem action='find'/>"
  "      <menuitem action='find-again'/>"
  "      <menuitem action='replace'/>"
  "      <separator/>"
  "      <menuitem action='properties'/>"
  "    </menu>"
  "    <menu action='help'>"
  "      <menuitem action='contents'/>"
  "      <menuitem action='about'/>"
  "    </menu>"
  "  </menubar>"
  "  <toolbar>"
  "    <toolitem action='new'/>"
  "    <separator/>"
  "    <toolitem action='prev'/>"
  "    <toolitem action='next'/>"
  "  </toolbar>"
  "</ui>";

static GtkActionEntry entries[] =
{
  { "file", NULL, N_("_File"), NULL, NULL, NULL },
  { "edit", NULL, N_("_Edit"), NULL, NULL, NULL },
  { "help", NULL, N_("_Help"), NULL, NULL, NULL },
  { "new", GTK_STOCK_NEW, N_("_New"), "<Ctrl>N", NULL, G_CALLBACK (new_action_callback) },
  { "open", GTK_STOCK_OPEN, N_("_Open"), "<Ctrl>O", NULL, G_CALLBACK (nothing_action_callback) },
  { "save", GTK_STOCK_SAVE, N_("_Save"), "<Ctrl>S", NULL, G_CALLBACK (nothing_action_callback) },
  { "save-as", GTK_STOCK_SAVE_AS, N_("Save _As"), "<Ctrl><Shift>S", NULL, G_CALLBACK (nothing_action_callback) },
  { "close", GTK_STOCK_CLOSE, N_("_Close"), "<Ctrl>W", NULL, G_CALLBACK (close_action_callback) },
  { "quit", GTK_STOCK_QUIT, N_("_Quit"), "<Ctrl>Q", NULL, G_CALLBACK (quit_action_callback) },
  { "cut", GTK_STOCK_CUT, N_("Cu_t"), "<Ctrl>X", NULL, G_CALLBACK (nothing_action_callback) },
  { "copy", GTK_STOCK_COPY, N_("_Copy"), "<Ctrl>C", NULL, G_CALLBACK (nothing_action_callback) },
  { "paste", GTK_STOCK_PASTE, N_("_Paste"), "<Ctrl>V", NULL, G_CALLBACK (nothing_action_callback) },
  { "select-all", NULL, N_("Select _All"), "<Ctrl>A", NULL, G_CALLBACK (nothing_action_callback) },
  { "clear", GTK_STOCK_CLEAR, N_("C_lear"), NULL, NULL, G_CALLBACK (nothing_action_callback) },
  { "undo", GTK_STOCK_UNDO, N_("_Undo"), "<Ctrl>Z", NULL, G_CALLBACK (nothing_action_callback) },
  { "redo", GTK_STOCK_REDO, N_("_Redo"), "<Ctrl><Shift>Z", NULL, G_CALLBACK (nothing_action_callback) },
  { "find", GTK_STOCK_FIND, N_("_Find"), "<Ctrl>F", NULL, G_CALLBACK (nothing_action_callback) },
  { "find-again", GTK_STOCK_FIND, N_("Find Ne_xt"), "<Ctrl>G", NULL, G_CALLBACK (nothing_action_callback) },
  { "replace", GTK_STOCK_FIND_AND_REPLACE, N_("R_eplace"), "<Ctrl>R", NULL, G_CALLBACK (nothing_action_callback) },
  { "properties", GTK_STOCK_PROPERTIES, N_("Pr_operties"), "<Ctrl>P", NULL, G_CALLBACK (nothing_action_callback) },
  { "contents", GTK_STOCK_HELP, N_("_Contents"), "F1", NULL, G_CALLBACK (nothing_action_callback) },
  { "about", GTK_STOCK_ABOUT, N_("_About"), NULL, NULL, G_CALLBACK (about_action_callback) },
  { "prev", GTK_STOCK_GO_BACK, N_("_Previous"), NULL, NULL, G_CALLBACK (nothing_action_callback) },
  { "next", GTK_STOCK_GO_FORWARD, N_("_Next"), NULL, NULL, G_CALLBACK (nothing_action_callback) },
};

static void 
nothing_action_callback (GtkAction* action, gpointer data)
{
  GtkWidget* dialog;
  GtkWidget* app;
  
  app = (GtkWidget*) data;

  dialog = gtk_message_dialog_new (GTK_WINDOW (app),
				   GTK_DIALOG_MODAL | GTK_DIALOG_DESTROY_WITH_PARENT,
				   GTK_MESSAGE_INFO,
				   GTK_BUTTONS_OK,
				   _("This does nothing; it is only a demonstration."));

  gtk_dialog_run (GTK_DIALOG (dialog));
  gtk_widget_destroy (dialog);
}

static void 
new_action_callback (GtkAction* action, gpointer data)
{
  GtkWidget* app;

  app = hello_app_new (_("Hello, World!"), NULL, NULL);

  gtk_widget_show_all (app);
}

static void 
close_action_callback (GtkAction* action, gpointer data)
{
  GtkWidget* app;

  app = (GtkWidget*) data;

  hello_app_close (app);
}

static void 
quit_action_callback (GtkAction* action, gpointer data)
{
  gtk_main_quit ();
}

static void 
about_action_callback (GtkAction* action, gpointer data)
{
  GtkWindow* app = GTK_WINDOW (data);
  const gchar *authors[] = {
    "Havoc Pennington <hp@pobox.com>",
    NULL
  };

  gtk_show_about_dialog (app,
                         "name", _("GNOME Hello"),
                         "version", VERSION,
                         "copyright", "\xc2\xa9 1999 Havoc Pennington",
                         "authors", authors,
                         "translator-credits", _("translator-credits"),
                         "logo-icon-name", "gnome-hello-logo",
                         NULL);
}

GtkUIManager *
create_ui_manager (const gchar *group, gpointer user_data)
{
  GtkActionGroup *action_group;
  GtkUIManager *ui_manager;
  GError *error;

  action_group = gtk_action_group_new (group);
  gtk_action_group_set_translation_domain(action_group, NULL);
  gtk_action_group_add_actions (action_group, entries, G_N_ELEMENTS (entries), user_data);
  ui_manager = gtk_ui_manager_new ();
  gtk_ui_manager_insert_action_group (ui_manager, action_group, 0);

  error = NULL;
  if (!gtk_ui_manager_add_ui_from_string (ui_manager, ui, -1, &error))
    {
      g_message ("Building menus failed: %s", error->message);
      g_error_free (error);
      exit (1);
    }

  return ui_manager;
}

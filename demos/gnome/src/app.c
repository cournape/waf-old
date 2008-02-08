/* app.c
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
#include "app.h"
#include "menus.h"

/* Keep a list of all open application windows */
static GSList *app_list = NULL;

static gint delete_event_cb (GtkWidget *w, GdkEventAny *e, gpointer data);
static void button_click_cb (GtkWidget *w, gpointer data);

GtkWidget * 
hello_app_new (const gchar *message, 
               const gchar *geometry,
               GSList      *greet)
{
  GtkWidget *app;
  GtkWidget *vbox;
  GtkWidget *button;
  GtkWidget *label;
  GtkWidget *menubar;
  GtkUIManager *ui_manager;
  GtkAccelGroup *accel_group;

  /*** gnomehello-widgets */
  app = gtk_window_new (GTK_WINDOW_TOPLEVEL);
  gtk_window_set_policy (GTK_WINDOW (app), FALSE, TRUE, FALSE);
  gtk_window_set_default_size (GTK_WINDOW (app), 250, 350);
  gtk_window_set_title (GTK_WINDOW (app), _("GNOME Hello"));
  gtk_window_set_wmclass (GTK_WINDOW (app), "hello", "GnomeHello");

  vbox = gtk_vbox_new (FALSE, 0);
  gtk_container_add (GTK_CONTAINER (app), vbox);

  ui_manager = create_ui_manager ("GnomeHelloActions", app);

  accel_group = gtk_ui_manager_get_accel_group (ui_manager);
  gtk_window_add_accel_group (GTK_WINDOW (app), accel_group);

  menubar = gtk_ui_manager_get_widget (ui_manager, "/menubar");
  gtk_box_pack_start (GTK_BOX (vbox), menubar, FALSE, FALSE, 0);

  button = gtk_button_new ();
  gtk_container_set_border_width (GTK_CONTAINER (button), 10);
  gtk_box_pack_start (GTK_BOX (vbox), button, TRUE, TRUE, 0);

  label  = gtk_label_new (message ? message : _("Hello, World!"));
  gtk_container_add (GTK_CONTAINER (button), label);

  g_signal_connect (G_OBJECT (app),
                    "delete_event",
                    G_CALLBACK (delete_event_cb),
                    NULL);

  g_signal_connect (G_OBJECT (button),
                    "clicked",
                    G_CALLBACK (button_click_cb),
                    label);
  
  if (geometry != NULL) 
    {
      if (!gtk_window_parse_geometry (GTK_WINDOW (app), geometry)) 
        {
          g_error (_("Could not parse geometry string `%s'"), geometry);
        }
    }

  if (greet != NULL)
    {
      GtkWidget *dialog;
      gchar *greetings = g_strdup (_("Special Greetings to:\n"));
      GSList *tmp = greet;

      while (tmp != NULL)
        {
          gchar *old = greetings;

          greetings = g_strconcat (old, 
                                   (gchar *) tmp->data,
                                   "\n",
                                   NULL);
          g_free (old);

          tmp = g_slist_next (tmp);
        }
      
      dialog = gtk_message_dialog_new (GTK_WINDOW (app),
				       GTK_DIALOG_DESTROY_WITH_PARENT,
				       GTK_MESSAGE_INFO,
				       GTK_BUTTONS_OK,
				       greetings,
				       NULL);
      g_signal_connect (dialog, "response",
			G_CALLBACK (gtk_object_destroy), NULL);
      gtk_widget_show (dialog);

      g_free (greetings);
    }

  app_list = g_slist_prepend (app_list, app);

  gtk_widget_show_all (vbox);

  return app;
}

void       
hello_app_close (GtkWidget *app)
{
  app_list = g_slist_remove (app_list, app);

  gtk_widget_destroy (app);

  if (app_list == NULL)
    {
      /* No windows remaining */
      gtk_main_quit ();
    }
}

static gint 
delete_event_cb (GtkWidget *window, GdkEventAny *e, gpointer data)
{
  hello_app_close (window);

  /* Prevent the window's destruction, since we destroyed it 
   * ourselves with hello_app_close()
   */
  return TRUE;
}

static void 
button_click_cb (GtkWidget *w, gpointer data)
{
  GtkWidget *label;
  const gchar *text;
  gchar *tmp;

  label = GTK_WIDGET (data);

  text = gtk_label_get_text (GTK_LABEL (label));

  tmp = g_utf8_strreverse (text, -1);

  gtk_label_set_text (GTK_LABEL (label), tmp);

  g_free(tmp);
}

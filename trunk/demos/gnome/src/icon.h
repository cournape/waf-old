/* icon.h
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

/*** gnomehello-iconh */

#ifndef GNOMEHELLO_ICON_H
#define GNOMEHELLO_ICON_H

typedef struct _GdkIconSize GdkIconSize;

struct _GdkIconSize {
  gint min_width;
  gint min_height;
  gint max_width;
  gint max_height;
  gint width_inc;
  gint height_inc;
};

void gdk_get_icon_sizes(GdkIconSize** size_list, guint* count);

void hello_set_icon(GtkWindow* window, const gchar* filename);
                         
#endif

/* gnomehello-iconh ***/

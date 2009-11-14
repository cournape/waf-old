/* icon.c
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

/*** gnomehello-icon */

#include <gnome.h>
#include <config.h>
#include <gdk/gdkx.h>
#include "icon.h"

void 
hello_set_icon(GtkWindow* window, const gchar* filename)
{
  /* Not implemented; wouldn't use gdk_get_icon_sizes() anyway */
}

void
gdk_get_icon_sizes(GdkIconSize** size_list, guint* count)
{
  XIconSize* xsizes;
  int xcount;

  if (XGetIconSizes (gdk_display, GDK_ROOT_WINDOW(), &xsizes, &xcount))
    {
      int i;

      g_assert (xcount > 0);

      *size_list = g_new (GdkIconSize, xcount);
      *count = (guint)xcount;

      i = 0;
      while (i < xcount)
        {
          (*size_list)[i].min_width  = xsizes[i].min_width;
          (*size_list)[i].min_height = xsizes[i].min_height;
          (*size_list)[i].max_width  = xsizes[i].max_width;
          (*size_list)[i].max_width  = xsizes[i].max_width;
          (*size_list)[i].width_inc  = xsizes[i].width_inc;
          (*size_list)[i].height_inc = xsizes[i].height_inc;

          ++i;
        }
    }
  else
    {
      *size_list = NULL;
      *count = 0;
    }
}

/* gnomehello-icon ***/

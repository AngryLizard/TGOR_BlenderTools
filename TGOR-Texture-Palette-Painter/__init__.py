
bl_info = {
    "name": "TGOR Palette Painting",
    "author": "Salireths, Hopfel",
    "version": (0, 0, 0),
    "blender": (2, 93, 0),
    "description": "Provides a palette to draw for the TGOR texturing system",
    "warning": "",
    "wiki_url": "",
    "category": "Object"
    }


import bpy
import bpy.utils.previews

from bpy.types import Operator, Panel, UIList, PropertyGroup
from bpy.props import PointerProperty, StringProperty, IntProperty, FloatProperty, BoolProperty, EnumProperty, FloatVectorProperty
from bpy.props import CollectionProperty, PointerProperty

icon_size = 4 # Preview icon density (higher setting will lag the editor)
icon_xmargin = 1 # Horizontal sampling marging for preview icons in case of fuzzy borders
icon_ymargin = 1 # Vertical sampling marging for preview icons in case of fuzzy borders

# Cell button name and tooltip, has to be 4 columns
palette_grid_cells = [
[("NoTip", "Nose Tip"), ("NoBk", "Nose Beak"), ("ArNos", "Around Nostrils"), ("InNos", "Inside Nostrils")],
[("Lips", "Lips"), ("Maw", "Maw"), ("Thro", "Throat"), ("Stom", "Stomach")],
[("Tailh", "Tailhole"), ("Ints", "Intestines"), ("Tong", "Tongue"), ("ToTip", "Tongue-Tip")],
[("SfSkn", "Soft-Skin (between legs / nipples / udders)"), ("GenLp", "Genital Lips (inside sheath / slit)"), ("OutGn", "Outer Genitalia"), ("InGen", "Inner Genitalia (womb / urethra)")],
[("AEyeF", "Around Eye Flesh"), ("EarO", "Ear Outside"), ("EarI", "Ear Inside"), ("EarC", "Ear Canal")],
[("FrntT", "Front Teeth"), ("CaniT", "Canine Teeth"), ("Premo", "Premolars"), ("Molrs", "Molars")],
[("PlmP", "Palm Pads"), ("FingP", "Finger Pads"), ("FingT", "Fingertips"), ("FingC", "Finger Claws")],
[("WinH", "Wing-Hand Pads"), ("WingP", "Singer Pads"), ("WingT", "Wingertips"), ("WingC", "Winger Claws")],
[("FeetP", "Feed Pads"), ("ToePa", "Toe Pads"), ("ToeTi", "Toe Tips"), ("ToeCl", "Toe Claws")],
[("WinDS", "Wing Dorsal Start"), ("WinDT", "Wing Dorsal Tip"), ("WinVT", "Wing Ventral Tip"), ("WinVS", "Wing Ventral Start")],
[("", ""), ("", ""), ("", ""), ("", "")],
[("", ""), ("", ""), ("", ""), ("", "")],
[("", ""), ("", ""), ("", ""), ("", "")],
[("HorBa", "HornBase"), ("HorSh", "Horn Short (or longs base)"), ("HorLB", "Horn Long Base (or shorts tip)"), ("HorLT", "Horn Long Tip")],
[("FeeTD", "Feet Tops Details"), ("BaTaB", "Back / Tail-Back (details)"), ("SAWT", "Shoulder / Arm / Wing Top (details)"), ("HeCra", "Head / Cranium (details)")],
[("FeeUS", "Feet under / Soles (details)"), ("BBPUD", "Belly / Bellyplates / Undertail (details)"), ("SAWU", "Shoulder / Arm / Wing under (details)"), ("HECHC", "Head / Chin / Cheek (details)")]
];


preview_collections = {}
preview_dirty = True

####################################################################################################
########################################### OPERATOR ###############################################
####################################################################################################

class TGOR_OT_PaletteColorSet(Operator):
    bl_label = "Palette Color Set"
    bl_idname = "scene.tgor_palette_set_operator"
    bl_description = "Set color from palette selection"
    
    color: FloatVectorProperty(name="color", subtype='COLOR')
    tooltip: bpy.props.StringProperty()
            
    @classmethod
    def description(cls, context, properties):
        return properties.tooltip
    
    def check(self, context):
        return True
    
    def execute(self, context):
        context.tool_settings.image_paint.brush.color = self.color
        context.tool_settings.image_paint.brush.blend = 'MIX'
        return {'FINISHED'}

class TGOR_OT_PaletteColorAdd(Operator):
    bl_label = "Palette Color Add"
    bl_idname = "scene.tgor_palette_add_operator"
    bl_description = "Set color to add"
    
    def check(self, context):
        return True
    
    def execute(self, context):
        context.tool_settings.image_paint.brush.color = (0,0,1)
        context.tool_settings.image_paint.brush.blend = 'ADD'
        return {'FINISHED'}
    
class TGOR_OT_PaletteColorSubtract(Operator):
    bl_label = "Palette Color Subtract"
    bl_idname = "scene.tgor_palette_subtract_operator"
    bl_description = "Set color to subtract"
    
    def check(self, context):
        return True
    
    def execute(self, context):
        context.tool_settings.image_paint.brush.color = (0,0,1)
        context.tool_settings.image_paint.brush.blend = 'SUB'
        return {'FINISHED'}

####################################################################################################
############################################# PANEL ################################################
####################################################################################################

class TGOR_PT_PalettePanel(Panel):
    """Palette group""" 
    bl_idname = "TGOR_PT_PalettePanel"
    bl_label = "Palette"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    
#   Draw the menu elements
    def draw(self, context):
        global preview_dirty
        layout = self.layout
        
        layout.template_ID(context.scene, "tgor_palette_image", new="image.new", open="image.open")
        preview = context.scene.tgor_palette_image
        
        row = layout.row(align=True)
        row.operator("scene.tgor_palette_add_operator", text="Add", icon="ADD")
        row.operator("scene.tgor_palette_subtract_operator", text="Subtract", icon="REMOVE")
        
        cols = 4
        rows = len(palette_grid_cells)
        
        icons = preview_collections["main"]
        
        grid = layout.grid_flow(row_major=True, columns=cols)
        for y, row in enumerate(palette_grid_cells):
            for x, (name, tooltip) in enumerate(row):
                if name != "":
                    
                    # Generate previews if available
                    if preview:
                        
                        icon = icons["icon" + str(y) + str(x)]
                            
                        if preview_dirty:
                            sx = (preview.size[0] / cols)
                            sy = (preview.size[1] / rows)
                            
                            for cx in range(0,icon_size):
                                for cy in range(0, icon_size):
                                    
                                    px = int(sx * x + icon_xmargin + (sx - icon_xmargin * 2) * cx / icon_size)
                                    py = int(sy * y + icon_ymargin + (sy - icon_ymargin * 2) * cy / icon_size)
                                    pi = ((preview.size[1]-1 - py) * preview.size[0] + px) * 4
                                    
                                    ci = ((icon_size-1 - cy) * icon_size + cx) * 4
                                    icon.icon_pixels_float[ci:ci+4] = preview.pixels[pi:pi+4]
                            
                        ops = grid.operator("scene.tgor_palette_set_operator", text=name, icon_value=icon.icon_id)
                    else:
                        ops = grid.operator("scene.tgor_palette_set_operator", text=name)
                    
                    # Sample in the middle of each swatch
                    ops.color = [(float(x) + 0.5) / (cols-1), (float(y) + 0.5) / rows, 0.0]
                    ops.tooltip = tooltip
        
        preview_dirty = False

    @classmethod
    def poll(cls, context):
        return context.mode == 'PAINT_TEXTURE'

classes = (
    TGOR_PT_PalettePanel,
    TGOR_OT_PaletteColorSet,
    TGOR_OT_PaletteColorAdd,
    TGOR_OT_PaletteColorSubtract
)

def on_palette_change(self, context):
    global preview_dirty
    preview_dirty = True

# Register
def register():
    global preview_dirty

    from bpy.utils import register_class
    for c in classes:
        register_class(c)
    
    bpy.types.Scene.tgor_palette_image = PointerProperty(type=bpy.types.Image, update=on_palette_change)
    preview_dirty = True
        
    icons = bpy.utils.previews.new()
    
    cols = 4
    rows = len(palette_grid_cells)
    for y in range(0, rows):
        for x in range(0, cols):
            icon = icons.new("icon" + str(y) + str(x))
            icon.icon_size = [icon_size, icon_size]
            icon.icon_pixels_float = [0.0, 0.0, 0.0, 1.0] * (icon_size * icon_size)
            icon.is_icon_custom = True
    
    preview_collections["main"] = icons

def unregister():
    
    preview_collections["main"] = {}
    
    for icons in preview_collections.values():
        bpy.utils.previews.remove(icons)
    preview_collections.clear()
    
    del bpy.types.Scene.tgor_palette_image
    
    from bpy.utils import unregister_class
    for c in reversed(classes):
        unregister_class(c)

if __name__ == "__main__":
    register()

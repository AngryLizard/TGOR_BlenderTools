
bl_info = {
    "name": "TGOR Vertex Coloriser",
    "author": "Salireths, Hopfel",
    "version": (0, 0, 0),
    "blender": (2, 93, 0),
    "description": "Sets vertex colors according to vertex groups",
    "warning": "",
    "wiki_url": "",
    "category": "Object"
    }

import bpy

from bpy.types import Operator, Panel, UIList, PropertyGroup
from bpy.props import CollectionProperty, PointerProperty, StringProperty, IntProperty, FloatProperty, BoolProperty, EnumProperty, FloatVectorProperty
from mathutils import Vector
import math

####################################################################################################
####################################### PROPERTY GROUP #############################################
####################################################################################################

class TGOR_VertexColorizationEntry(PropertyGroup):
    
    red: FloatProperty(default=0.0, min=0.0, max=1.0)
    green: FloatProperty(default=0.0, min=0.0, max=1.0)
    blue: FloatProperty(default=0.0, min=0.0, max=1.0)
    alpha: FloatProperty(default=1.0, min=0.0, max=1.0)
    weight: FloatProperty(default=1.0, min=0.01, max=5.0)
    
class TGOR_VertexColorizationOptions(PropertyGroup):
    
    red: BoolProperty(default=True)
    green: BoolProperty(default=True)
    blue: BoolProperty(default=False)
    alpha: BoolProperty(default=False)
    
####################################################################################################
########################################### OPERATOR ###############################################
####################################################################################################

class TGOR_OT_VertexColorization(Operator):
    bl_label = "Compute Vertex Colors"
    bl_idname = "scene.tgor_vertex_colorization_operator"
    bl_description = "Compute vertex colors from vertex groups"
    
    def check(self, context):
        return True
    
    def execute(self, context):
        return {'FINISHED'}


class TGOR_OT_AddVertexGroup(Operator):
    bl_label = "Add Colorizer Group"
    bl_idname = "scene.tgor_add_vertex_group_operator"
    bl_description = "Add vertex group to colorization list"
    
    def check(self, context):
        return True
    
    def execute(self, context):
        selection = context.scene.tgor_vertex_group_selection
        
        if selection != "":
            
            for colorization in context.scene.tgor_vertex_colorizations:
                if colorization.name == selection:
                    self.report({'ERROR_INVALID_INPUT'}, "Already added that group")
                    return {'FINISHED'}	
            
            colorization = context.scene.tgor_vertex_colorizations.add()
            colorization.name = selection
                        
        return {'FINISHED'}
    
    
class TGOR_OT_RemoveVertexGroup(Operator):
    bl_label = "Remove Colorizer Group"
    bl_idname = "scene.tgor_remove_vertex_group_operator"
    bl_description = "Remove vertex group to colorization list"
        
    def check(self, context):
        return True
    
    def execute(self, context):
                
        selection = context.scene.tgor_vertex_colorization_index
        
        if selection != -1:
            context.scene.tgor_vertex_colorizations.remove(selection)
                        
        return {'FINISHED'}
    
    
class TGOR_OT_ColorizeVertices(Operator):
    bl_label = "Colorize Vertex Groups"
    bl_idname = "scene.tgor_colorize_operator"
    bl_description = "Colorize according to assigned vertex groups"
    
    iterations: IntProperty(default=20, min=1)
    color_selection: StringProperty()
    weighting : EnumProperty(
        items=(
            ('POLY', 'Polynomial', "Polynomial interpolation"),
            ('LAPL', 'Laplacian', "Laplacian interpolation")
        ),
        name="Weighting algorithm",
        description="Choose weight algorithm",
        default='POLY',
        update=None,
        get=None,
        set=None)
        
        
        
    
    def check(self, context):
        return True
    
    def invoke(self, context, event):
        
        self.color_selection = context.active_object.data.vertex_colors.active.name
        wm = context.window_manager  # there are some other functions here
        return wm.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.prop(self, "weighting", text="Weighting")
        row.prop(self, "iterations", text="Iterations")
        layout.prop_search(self, "color_selection", context.active_object.data, "vertex_colors", text="", icon='COLOR')
        
    
    def execute(self, context):
        
        # Decide which vertex color map to use
        vertex_color = context.active_object.data.vertex_colors.active
        if self.color_selection in context.active_object.data.vertex_colors:
            vertex_color = context.active_object.data.vertex_colors[self.color_selection]
        
        if not vertex_color:
            self.report({'ERROR_INVALID_INPUT'}, "No vertex color selected or active")
            return {'FINISHED'}
            
        diameter = max(context.active_object.dimensions)
        count = len(context.active_object.data.vertices)
        
        # Triangulate
        context.active_object.data.calc_loop_triangles()
        
        # Establish mesh relations
        E = set() # Triangulation edges
        V = [[]] * count # Triangulation edges
        for triangle in context.active_object.data.loop_triangles:
            for (i, j) in [(0, 1), (1, 2), (2,0)]:
                u = triangle.vertices[i]
                v = triangle.vertices[j]
                
                uc = context.active_object.data.vertices[u].co
                vc = context.active_object.data.vertices[v].co
                w = (uc-vc).length
                
                E.add((u, v, w))
                V[u].append((v, w))
        
        # Build groups
        U = set() # All vertices outside of groups
        G = {key: [] for key in context.scene.tgor_vertex_colorizations.keys()} # Vertices per group
        for vertex in context.active_object.data.vertices:
            U.add(vertex.index)   
            for group in vertex.groups:
                if group.weight > 0.1:
                    name = context.active_object.vertex_groups[group.group].name
                    if name in context.scene.tgor_vertex_colorizations:
                        G[name].append(vertex.index)
                        U.remove(vertex.index)
                        break
                
        # Build shortest paths for each group
        C = [Vector((0,0,0,1))] * count # Output Colors
        D = {} # Vertex min path distances for each group
        W = {} # Weight for each group
        O = {} # output color for each group
        for name, group_vertices in G.items():
            
            d = [diameter] * count
            
            for group_vertex in group_vertices:
                colorization = context.scene.tgor_vertex_colorizations[name]
                
                color = Vector((colorization.red, colorization.green, colorization.blue, colorization.alpha))
                C[group_vertex] = O[name] = color
                W[name] = colorization.weight
                
                # Start every vertex from the group with zero weight
                d[group_vertex] = 0.0
            
            # Execute bellman-ford algorithm for each vertex (CPU go brrrr)
            for i in range(1, self.iterations):
                for u, v, w in E:
                    t = d[u] + w
                    if t < d[v]:
                        d[v] = t
                        
            D[name] = d
        
        # Build vertex colors for yet unassigned vertices
        for u in U:
            
            if self.weighting == 'POLY':
                c = Vector((0,0,0,0))
                for name in G:
                    
                    d = D[name][u] / W[name]
                    
                    f = 1.0
                    for other in G:
                        if other != name:
                            e = D[other][u] / W[other]
                            f *= e / (d + e)
                            
                    c += O[name] * f
                
                C[u] = c
                
            else:
                w = 0.0
                c = Vector((0,0,0,0))
                for name in G:
                    
                    d = D[name][u]
                    
                    f = W[name] / max(d, 0.0001) # Avoid division by zero
                    c += O[name] * f
                    w += f
                
                if w > 0.0001:
                    C[u] = c / w
        
        # Actually set the color according to defined mask
        for loop in context.active_object.data.loops:
            if context.scene.tgor_vertex_options.red:
                vertex_color.data[loop.index].color[0] = C[loop.vertex_index][0]
            if context.scene.tgor_vertex_options.green:
                vertex_color.data[loop.index].color[1] = C[loop.vertex_index][1]
            if context.scene.tgor_vertex_options.blue:
                vertex_color.data[loop.index].color[2] = C[loop.vertex_index][2]
            if context.scene.tgor_vertex_options.alpha:
                vertex_color.data[loop.index].color[3] = C[loop.vertex_index][3]
        
                        
        return {'FINISHED'}
    
####################################################################################################
############################################ UIList ################################################
####################################################################################################
    
class TGOR_UL_vertex_colorization_list(UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        
        split = layout.split(factor=0.25)
        split.label(text=item.name)
        row = split.row()
        row.prop(item, "red", text="")
        row.prop(item, "green", text="")
        row.prop(item, "blue", text="")
        row.prop(item, "alpha", text="")
        row.prop(item, "weight", text="")

    def invoke(self, context, event):
        pass  

####################################################################################################
############################################# PANEL ################################################
####################################################################################################

class TGOR_PT_VertexColorizationPanel(Panel):
    """Palette group""" 
    bl_idname = "TGOR_PT_VertexColorizationPanel"
    bl_label = "Colorization"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    
#   Draw the menu elements
    def draw(self, context):
        layout = self.layout
        
        col = self.layout.column(align=True)

        row = col.row(align=True)
        row.label(text="Selected Vertex Groups:")

        row = col.row(align=True)
        if context.scene.tgor_vertex_colorization_index != -1:
            row.operator("scene.tgor_remove_vertex_group_operator", text="", icon='REMOVE')
        if context.scene.tgor_vertex_group_selection != "":
            row.operator("scene.tgor_add_vertex_group_operator", text="", icon='ADD')
        row.prop_search(context.scene, "tgor_vertex_group_selection", context.active_object, "vertex_groups", text="", icon='GROUP_VERTEX')
        
        
        split = col.split(factor=0.25)
        split.label(text="Mask")
        row = split.row()
        row.prop(context.scene.tgor_vertex_options, "red", text="Red")
        row.prop(context.scene.tgor_vertex_options, "green", text="Green")
        row.prop(context.scene.tgor_vertex_options, "blue", text="Blue")
        row.prop(context.scene.tgor_vertex_options, "alpha", text="Alpha")
        row.label(text="Weight")
        
        row = col.row(align=True)
        row.template_list("TGOR_UL_vertex_colorization_list", "", context.scene, "tgor_vertex_colorizations", context.scene, "tgor_vertex_colorization_index", rows=4)
        
        col.separator()
        if len(context.scene.tgor_vertex_colorizations) > 0:
            row = col.row(align=True)
            row.operator("scene.tgor_colorize_operator", text="Colorize Vertex Groups")
        
        col = row.column(align=True)
        
    @classmethod
    def poll(cls, context):
        return context.mode == 'PAINT_VERTEX' and context.active_object and context.active_object.type == 'MESH'

classes = (
    TGOR_PT_VertexColorizationPanel,
    TGOR_OT_VertexColorization,
    TGOR_OT_AddVertexGroup,
    TGOR_OT_RemoveVertexGroup,
    TGOR_OT_ColorizeVertices,
    TGOR_VertexColorizationEntry,
    TGOR_VertexColorizationOptions,
    TGOR_UL_vertex_colorization_list
)


# Register
def register():

    from bpy.utils import register_class
    for c in classes:
        register_class(c)
        
    bpy.types.Scene.tgor_vertex_group_selection = StringProperty()
    bpy.types.Scene.tgor_vertex_colorizations = CollectionProperty(type=TGOR_VertexColorizationEntry)
    bpy.types.Scene.tgor_vertex_colorization_index = IntProperty()
    bpy.types.Scene.tgor_vertex_options = PointerProperty(type=TGOR_VertexColorizationOptions)

def unregister():
    
    del bpy.types.Scene.tgor_vertex_options
    del bpy.types.Scene.tgor_vertex_colorization_index
    del bpy.types.Scene.tgor_vertex_colorizations
    del bpy.types.Scene.tgor_vertex_group_selection
    
    from bpy.utils import unregister_class
    for c in reversed(classes):
        unregister_class(c)

if __name__ == "__main__":
    register()

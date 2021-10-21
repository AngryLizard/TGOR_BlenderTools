import bpy

from bpy.props import FloatProperty
from bpy.types import Operator
from mathutils import Vector
import functools

bl_info = {
    "name": "TGOR Normal Merger",
    "author": "Hopfel)",
    "version": (1, 0),
    "blender": (2, 93, 0),
    "description": "Allows merging normals of one base mesh and multiple optional meshes",
    "warning": "",
    "wiki_url": "",
    "category": "Object"
    }

# Toggle edit operator
class TGOR_OT_NormalMerge(Operator):
    """Merge normals between Active and selected objects """
    bl_idname = "object.normal_merge"
    bl_label = "Normal Merge Operator"
    bl_options = {'REGISTER', 'UNDO'}
    
    tolerance: FloatProperty(default=0.0001)

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        
        base = context.active_object
        if base.type == 'MESH':
            
            base.data.calc_normals_split()
            output = [None] * len(base.data.vertices)
            
            objects = [o for o in context.selected_objects if o.type == 'MESH' and not o is base]
            for object in objects:
                object.data.calc_normals_split()
            
            targets = [(o, list(map(lambda loop: loop.normal, o.data.loops))) for o in objects]
            if len(targets) > 0:
                
                for reference in base.data.vertices:
                    
                    others = [(normals, loop, vertex) for (object, normals) in targets for loop in object.data.loops if (reference.co - (vertex:=object.data.vertices[loop.vertex_index]).co).length < self.tolerance]
                    if len(others) > 0:
                        
                        # Tuple unpacking not supported in python3 anymore, omega sadge
                        normal = (functools.reduce(lambda v, t: v + t[2].normal, others, Vector()) / len(others) + reference.normal).normalized()
                        
                        output[reference.index] = normal
                            
                        for (normals, loop, vertex) in others:
                            normals[loop.index] = normal
                    
                for (object, normals) in targets:
                    object.data.normals_split_custom_set(normals)
                
                base.data.normals_split_custom_set(list(map(lambda loop: output[loop.vertex_index] if output[loop.vertex_index] else loop.normal, base.data.loops)))
                
            else:
                self.report({'ERROR'}, "No objects to merge with selected.")
            
        else:
            self.report({'ERROR'}, "Active object has to be a mesh object.")
            

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(TGOR_OT_NormalMerge.bl_idname)
    

def register():
    
    bpy.utils.register_class(TGOR_OT_NormalMerge)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():

    bpy.utils.unregister_class(TGOR_OT_NormalMerge)
    

if __name__ == "__main__":
            
    register()

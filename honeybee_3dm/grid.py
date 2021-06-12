"""Create Honeybee grid objects from objects in a rhino file."""


import rhino3dm
import csv
import os
from honeybee_radiance.sensorgrid import SensorGrid
from honeybee.typing import clean_and_id_string, clean_string

from .togeometry import mesh_to_mesh3d, to_face3d
from .layer import objects_on_layer, objects_on_parent_child


class DataWriter:
    def __init__(self, name, data, target_folder=None):
        self.name = name
        self.data = data
        self.target_folder = target_folder

    def write_csv(self):
        # if target_folder is provided
        if self.target_folder:
            # validate target folder
            if not os.path.exists(self.target_folder):
                raise ValueError(
                    'Target foldder is not a valid path.'
                )
            file_name = os.path.join(self.target_folder, self.name + '.csv')
        else:
            file_name = self.name + '.csv'

        with open(file_name, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',')

            for data in self.data:
                csv_writer.writerow(data)


def import_grids(
        rhino3dm_file, layer, tolerance, *, grid_controls=None, child_layer=False):
    """Creates Honeybee grids from a rhino3dm file.

    This function assumes all the grid objects are under a layer named ``grid``.

    Args:
        rhino3dm_file: The rhino file from which Honeybee grids will be created.
        layer: A Rhino3dm layer object.
        tolerance: A rhino3dm tolerance object. Tolerance set in the rhino file.
        grid_controls: A tuple of values for grid_size and grid_offset.
            Defaults to None. This will employ the grid setting of (1.0, 1.0, 0.0)
            for grid-size-x, grid-size-y, and grid-offset respectively.
        child_layer: A bool. True will generate grids from the objects on the child layer
            of a layer in addition to the objects on the parent layer. Defaults to False.

    Returns:
        A list of Honeybee grids.
    """
    hb_grids = []
    grid_pos = []
    grid_dir = []
    data = []

    # if objects on child layers are not requested
    if not child_layer:
        grid_objs = objects_on_layer(rhino3dm_file, layer)

    # if objects on child layers are requested
    if child_layer:
        grid_objs = objects_on_parent_child(rhino3dm_file, layer.Name)

    # Set default grid settings if not provided
    if not grid_controls:
        grid_controls = (1.0, 1.0, 0.0)

    for obj in grid_objs:
        geo = obj.Geometry

        # If it's a Mesh use it to create grids
        # This is done so that if a user has created mesh with certain density
        # the same can be used to create grids
        if isinstance(geo, rhino3dm.Mesh):
            raise ValueError(
                'Mesh is not accepted.'
            )

        else:
            try:
                faces = to_face3d(obj, tolerance)
            except AssertionError:
                raise AssertionError(
                    f'Please check object with ID: {obj.Attributes.Id}.'
                    ' Either the object has faces too small for the grid size, or the'
                    ' object is not supported for grids. You should try again with a'
                    ' smaller grid size in the config file.'
                )
            name = obj.Attributes.Name
            obj_name = name or clean_and_id_string('Grid')
            args = [
                clean_string(obj_name), faces, grid_controls[0], grid_controls[0],
                grid_controls[1]]

            sens = SensorGrid.from_face3d(*args)
            pos = [item.pos for item in sens]
            dir = [item.dir for item in sens]
            grid_pos += pos
            grid_dir += dir

            data.append([obj_name, len(sens)])

    hb_grids.append(SensorGrid.from_position_and_direction(
                    identifier=layer.Name, positions=grid_pos, directions=grid_dir))

    return hb_grids, data

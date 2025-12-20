from build123d import *
import math


class Tripod:
    """Parametric tripod for a camera-tracked pendulum.

    Coordinate convention
    ---------------------
    - Global Z axis is vertical.
    - Legs extend downward (mostly in -Z), splayed by `leg_open_angle`.
    - Tables are placed relative to `Hmax`, the approximate height from the
      pivot-hole region (near the top part) to the ground plane.

    Notes on booleans
    -----------------
    In build123d, accumulating shapes via plain `+` can produce containers
    (e.g., ShapeList/Compound-like results) that are still geometrically valid
    but may behave unexpectedly under boolean operations. To keep booleans
    robust, this script prefers to accumulate into `Part()` objects.
    """

    def __init__(self):
        # =====================
        # Global / printing
        # =====================
        self.tol = 0.4  # clearance tolerance (mm) for 3D printing

        # =====================
        # Tripod top part
        # =====================
        self.R_top = 60.0          # circumradius of the top triangle
        self.H_top = 10.0          # thickness (Z) of the top triangle
        self.R_fillet_top = 10.0   # corner fillet radius on the top triangle

        # Pivot cone (string outlet)
        self.R1_Cone_top = 8.0
        self.R2_Cone_top = 1.0
        self.Cone_top_height = 3.0
        self.Cone_top_width = 2.0

        # =====================
        # Legs
        # =====================
        self.leg_length = 250.0
        self.leg_width = 15.0
        self.leg_in_width = 5.0
        self.leg_body_fillet = 5.0
        self.legHead_extend = 4.0
        self.leg_open_angle = 20.0

        # Leg socket depth into the top part (for assembly)
        self.leg_hole_top = 2.0

        # Radial position of the *centerline* of legs at the top part
        self.R_legs_top = self.R_top - self.R_fillet_top - self.leg_width - 5

        # Placement angles of the three legs
        self.leg_angles_deg = [0.0, 120.0, -120.0]

        # Precompute trig for leg opening
        self.cosA = math.cos(math.radians(self.leg_open_angle))
        self.sinA = math.sin(math.radians(self.leg_open_angle))

        # =====================
        # Camera & lens dimensions
        # =====================
        self.camera_cable = 20.0
        self.camera_body_width = 37.7
        self.camera_body_height = 33.0
        self.camera_lens_r = 15.0
        self.camera_lens_h = 41.0

        # =====================
        # Tables and camera holding features
        # =====================
        self.tables_H = 7.0
        self.bot_table_R = 50.0
        self.top_table_R = 40.0
        self.top_table_R_hole = self.camera_lens_r + 1.0

        # Bottom-table camera holder (square wall)
        self.bot_table_cam_hold_wall_width = 5.0
        self.bot_table_cam_hold_wall_height = 15.0

        # How much the top ring goes "into" the lens region
        self.table_top_hole_go_in_lens = 5.0

        # Bottom-table wall support (triangular rib)
        self.cam_hold_wall_support_width = 4.0
        self.cam_hold_wall_support_length = 0.6 * self.camera_body_width

        # Pillars between bottom and top table
        self.pillar_R = 3.0
        self.pillar_position_R = 32.0
        self.alpha_pillar = -30.0

        # =====================
        # Derived heights
        # =====================
        # Approx. height (pivot region to ground) given leg length and opening
        self.Hmax = self.leg_length * self.cosA - self.leg_hole_top - self.legHead_extend / 2

        self.L_cam = self.camera_body_height + self.camera_lens_h
        self.H_tot_cam = self.L_cam + self.camera_cable

        # =====================
        # "Magic" offsets -> named constants
        # =====================
        self.leg_x_bias = -1.5          # small X bias used for leg-top geometry alignment
        self.leg_bot_x_bias = -1.0      # small X bias for leg bottom block
        self.table_azimuth_offset = -60 # rotate the table assembly to align connectors visually
        self.cam_wall_cut_z_bias = 4.0  # extra vertical bias for the camera-holder wall cut

    # -----------------------------
    # Helpers
    # -----------------------------
    def _polar_xy(self, r: float, angle_deg: float) -> tuple[float, float]:
        a = math.radians(angle_deg)
        return (r * math.cos(a), r * math.sin(a))

    def _leg_transform(self, angle_deg: float) -> Location:
        """World transform to place a local leg at the correct top location."""
        x, y = self._polar_xy(self.R_legs_top, angle_deg)
        return Pos(x, y, self.leg_hole_top) * Rot(0, 0, angle_deg)

    # ===============================================
    def Build_top(self, smooth: bool = True) -> Part:
        """Construct the top tripod part.

        - Regular triangle with filleted corners.
        - Conical pivot hole (outer cone minus inner cone) for the pendulum string.
        - Three rectangular sockets (holes) to receive the printed legs.
        """
        top2d = RegularPolygon(radius=self.R_top, side_count=3)
        top2d = fillet(top2d.vertices(), self.R_fillet_top)

        top = Part() + extrude(top2d, self.H_top)

        # Cone outer (added) minus cone inner (subtracted) => conical hole with thickness
        cone_loc = Pos(0, 0, (self.H_top - self.Cone_top_height) / 2) * Rot(180, 0, 0)
        top += cone_loc * Cone(
            self.R1_Cone_top + self.Cone_top_width,
            self.R2_Cone_top + self.Cone_top_width,
            self.H_top + self.Cone_top_height,
        )
        top -= cone_loc * Cone(
            self.R1_Cone_top,
            self.R2_Cone_top,
            self.H_top + self.Cone_top_height,
        )
        
        if smooth:
            # These edge groups are based on the current topology; if geometry changes
            # substantially, revisit the slicing.
            top = fillet(top.edges().sort_by(Axis.Z)[4:], 2)
            top = fillet(top.edges().sort_by(Axis.Z)[:2], 0.5)

        # text
        top_plane = Plane(top.faces().sort_by(Axis.Z).last)
        txt = top_plane*Text("FSHN Fizike",8,font="DejaVu Sans",font_style=FontStyle.BOLD)
        txt = Pos(2*self.R_legs_top*math.cos(20)/3,-2*self.R_legs_top*math.sin(20)/3,0)*Rot(0,0,30)*extrude(txt,-1.)
        top -= txt
        top -= Rot(0,0,120)*txt
        top -= Rot(0,0,240)*txt
        
        # Leg sockets (clearance included)
        sock_w = self.leg_width + self.legHead_extend + self.tol
        sock = Pos(self.leg_x_bias, 0, 0) * extrude(Rectangle(sock_w, sock_w), -self.leg_hole_top)
        
        for ang in self.leg_angles_deg:
            x, y = self._polar_xy(self.R_legs_top, ang)
            top -= Pos(x, y, self.leg_hole_top) * Rot(0, 0, ang) * sock

        return top

    # ===============================================
    def table_tripod_connection_legs(self, smooth: bool = True) -> Part:
        """Construct ONE bridge (connector) from table to a leg.

        This part is used in two places:
        1) Added to the table assembly (three copies at 120°)
        2) Subtracted from each leg to create an alignment recess for gluing.

        Geometry:
        - A rectangular beam (extruded)
        - Plus a triangular pad (extruded) providing stiffness / glue area.
        """
        table_foot_L = 2 * ((self.Hmax + self.tables_H - self.camera_cable) * self.sinA - self.bot_table_R) + 2
        hfoot = 10
        xyfoot = 2

        rr = Plane.YZ * Rectangle(xyfoot * self.tables_H, self.tables_H)
        rr2 = Plane.XZ * Pos(table_foot_L - 0.4 * hfoot, 0, -xyfoot * self.tables_H / 2) * Rot(
            0, 0, 180 + self.leg_open_angle
        ) * RegularPolygon(radius=hfoot, side_count=3)

        obj = Part() + extrude(rr, table_foot_L)
        obj += extrude(rr2, xyfoot * self.tables_H)

        if smooth:
            obj = fillet(obj.edges().group_by(Axis.X)[1:], 2)

        return Pos(
            self.bot_table_R, 0, -self.Hmax + self.tables_H + self.camera_cable - self.tables_H / 2
        ) * obj

    # ===============================================
    def Leg(self, smooth: bool = True) -> Part:
        """Construct one tripod leg.

        - Hollow square tube body, tilted by `leg_open_angle`.
        - A top "head" block (fits into top-part socket).
        - A bottom "foot" block (stability).
        - A recess cut to accept the bridge connector for alignment/gluing.
        """
        # Hollow square cross-section
        body2d = Rectangle(self.leg_width, self.leg_width) - Rectangle(
            self.leg_width - self.leg_in_width,
            self.leg_width - self.leg_in_width,
        )
        body2d = fillet(body2d.vertices(), self.leg_body_fillet)

        # Body: tilt and extrude downward
        body = Part() + Rot(0, -self.leg_open_angle, 0) * extrude(body2d, -self.leg_length)

        # Trim top and bottom to cleanly mate with top plate / ground
        body -= extrude(Rectangle(1.5 * self.leg_width, 1.5 * self.leg_width), self.leg_width * self.sinA)
        body -= Pos(self.leg_length * self.sinA, 0, -self.leg_length * self.cosA) * Box(
            1.5 * self.leg_width,
            1.5 * self.leg_width,
            self.leg_width * self.sinA,
        )

        # Top and bottom blocks
        leg_top = Pos(self.leg_x_bias, 0, 0) * extrude(
            Rectangle(self.leg_width + self.legHead_extend, self.leg_width + self.legHead_extend),
            -(self.leg_width + 2) / 2 * self.sinA,
        )
        leg_bot = Pos(self.leg_length * self.sinA + self.leg_bot_x_bias, 0, -self.leg_length * self.cosA + self.legHead_extend) * Box(
            self.leg_width + self.legHead_extend,
            self.leg_width + self.legHead_extend,
            self.legHead_extend,
        )

        if smooth:
            leg_top = fillet(leg_top.edges().sort_by(Axis.Z)[:8], 1)
            leg_bot = fillet(leg_bot.edges().sort_by(Axis.Z)[4:8], 4)
            leg_bot = fillet(leg_bot.edges(), 1)

        leg = Part() + (body + leg_top + leg_bot)

        # Alignment recess for bridge connector
        bridge = self.table_tripod_connection_legs(smooth)
        leg -= Pos(-self.R_legs_top, 0, -self.leg_hole_top) * bridge

        return leg

    # ===============================================
    def tripod_legs(self, smooth: bool = True) -> Part:
        """Construct the three legs placed at 0°, 120°, -120°."""
        leg_local = self.Leg(smooth)
        legs = Part()
        for ang in self.leg_angles_deg:
            legs += self._leg_transform(ang) * leg_local
        return legs

    # ===============================================
    def table_Bottom(self, smooth: bool = True) -> Part:
        """Construct the bottom camera table.

        Components:
        - Base disk.
        - Square camera-holder wall with cable cutout.
        - Three triangular ribs supporting the holder wall.
        - Three pillars that support the top ring.
        - Three bridge connectors to tripod legs.
        """
        table_bot = Part() + extrude(Circle(self.bot_table_R), -self.tables_H)

        # Camera-holder wall (square ring)
        outer_w = self.camera_body_width + self.bot_table_cam_hold_wall_width
        inner_w = self.camera_body_width + self.tol
        wall2d = Part() + Rectangle(outer_w, outer_w)
        wall2d -= Rectangle(inner_w, inner_w)
        table_bot += extrude(wall2d, self.bot_table_cam_hold_wall_height)

        # One side opening for camera screw access / assembly clearance
        table_bot -= Pos(inner_w / 2, 0, self.bot_table_cam_hold_wall_height / 2 + self.cam_wall_cut_z_bias) * Box(
            self.bot_table_cam_hold_wall_width,
            inner_w,
            self.bot_table_cam_hold_wall_height,
        )

        # USB cable slot
        cabUSB = Part() + Pos(
            (self.bot_table_R + self.camera_body_width) / 2 - 5,
            0,
            (self.bot_table_cam_hold_wall_height - self.tables_H) / 2,
        ) * Box(
            self.bot_table_R,
            2.2 + self.tol,
            self.tables_H + self.bot_table_cam_hold_wall_height,
        )
        table_bot -= cabUSB

        if smooth:
            table_bot = fillet(table_bot.edges().filter_by(lambda f: f.length >= 2), 1.1)

        # Triangular wall supports (3 copies)
        rib = Pos(-self.cam_hold_wall_support_length / 2, 0, 0) * Rot(90, 90, 0) * extrude(
            make_face(
                Polyline(
                    [
                        (0, 0),
                        (0, 2 * self.cam_hold_wall_support_width),
                        (self.cam_hold_wall_support_width, 0),
                        (0, 0),
                    ]
                )
            ),
            self.cam_hold_wall_support_length,
        )
        XY = outer_w / 2
        table_bot += Pos(0, XY, 0) * rib
        table_bot += Rot(0, 0, 90) * Pos(0, XY, 0) * rib
        table_bot += Rot(0, 0, 180) * Pos(0, XY, 0) * rib

        # Pillars (3 copies)
        pillar2d = Rot(0, 0, self.alpha_pillar) * Pos(0, self.pillar_position_R, 0) * Circle(self.pillar_R)
        pillar2d += Rot(0, 0, self.alpha_pillar + 120) * Pos(0, self.pillar_position_R, 0) * Circle(self.pillar_R)
        pillar2d += Rot(0, 0, self.alpha_pillar - 120) * Pos(0, self.pillar_position_R, 0) * Circle(self.pillar_R)
        pillar = Part() + extrude(pillar2d, self.L_cam - self.table_top_hole_go_in_lens)

        # Bridge connectors (3 copies)
        bridge = self.table_tripod_connection_legs(smooth)
        bridges = Part() + bridge + Rot(0, 0, 120) * bridge + Rot(0, 0, -120) * bridge

        # Place the bottom table at the required height; rotate for better alignment
        placed = Rot(0, 0, self.table_azimuth_offset) * Pos(0, 0, -self.Hmax + self.tables_H + self.camera_cable) * (table_bot + pillar)

        return Part() + placed + bridges

    # ===============================================
    def table_Top(self, smooth: bool = True) -> Part:
        """Construct the top ring table that lightly holds the camera lens."""
        ring = Part() + Pos(0, 0, self.L_cam - self.table_top_hole_go_in_lens) * extrude(
            Circle(self.top_table_R) - Circle(self.top_table_R_hole),
            self.tables_H,
        )
        if smooth:
            ring = fillet(ring.edges(), 1.1)
        return Pos(0, 0, -self.Hmax + self.tables_H + self.camera_cable) * ring

    # ===============================================
    def table(self, smooth: bool = True) -> Part:
        """Construct the full camera table assembly (bottom + pillars + top ring + bridges)."""
        return Part() + self.table_Bottom(smooth) + self.table_Top(smooth)



def export_print_parts(tripod):
    """
    Export the printable parts of the tripod as separate STL files.

    Expected build methods in Tripod class:
      - tripod.Build_top()
      - tripod.Leg()                  -> one leg (single part)
      - tripod.Build_table_bot()       -> bottom plate + 3 pillars + 3 bridges (single part)
      - tripod.Build_table_top()       -> top table (single part)

    Notes:
    - Legs are exported 3x as identical STLs with different filenames.
    - We wrap exports in Part() to avoid ShapeList boolean/export quirks.
    """
    # Build parts
    top = Part() + tripod.Build_top()
    leg = Part() + tripod.Leg()
    table_bot = Part() + tripod.table_Bottom()
    table_top = Part() + tripod.table_Top()
    # Export
    folder = "./STL/"
    export_stl(top,folder+"tripod_top.stl")
    export_stl(leg,folder+"tripod_leg_1.stl")
    export_stl(leg,folder+"tripod_leg_2.stl")
    export_stl(leg,folder+"tripod_leg_3.stl")
    export_stl(table_bot,folder+"tripod_table_bottom.stl")
    export_stl(table_top,folder+"tripod_table_top.stl")
    print("Exported STLs to 'STL/' folder")




# ---------------------------------
# Script usage / preview
# ---------------------------------
if __name__ == "__main__":
    save = False
    smooth = True
    tr = Tripod()
    if save:
        export_print_parts(tr)
    top = tr.Build_top(smooth)
    legs = tr.tripod_legs(smooth)
    table = tr.table(smooth)
    show_object(top, options=dict(alpha=0.0))
    show_object(legs, options=dict(alpha=0.0, color="red"))
    show_object(table, options=dict(alpha=0.0, color="cyan"))



from build123d import *
import math

class Tripod:
    def __init__(self):
        self.tol = 0.4  # tolerance (for 3d printing)
        #-----------
        # Tripod top part parameters
        self.R_top           = 60.0 # radius of the regular polygon (triangle)
        self.H_top           = 10.0 # height or width of the top triangle
        self.R_fillet_top    = 10.0 # float (the radius of the fillet of the top
        self.R1_Cone_top     = 8.0  # upper and larger cone radius for the pendulum string hole
        self.R2_Cone_top     = 1.0  # lower and smaller cone radius for the pendulum string hole
        self.Cone_top_height = 3.0  # the length the cone extends downwards below the top
        self.Cone_top_width  = 2.0  # the width of the cone at the bottom hole
        #----------
        # legs parameters
        self.leg_length      = 250. # leg length
        self.leg_width       = 15.  # leg outer width, is a square cross section
        self.leg_in_width    = 5.   # leg inner width of the material (is empty in the middle)
        self.leg_body_fillet = 5.   # leg body cross sectional area vertex fillet
        self.legHead_extend  = 4.   # leg head/foot extend outside leg width
        self.leg_open_angle  = 20.  # leg opening angle with respect to the vertical line
        self.leg_hole_top    = 2.   # legs hole on the top part (good for assembling after 3D printing)
        self.R_legs_top = self.R_top-self.R_fillet_top-self.leg_width-5 # radius of position of the cnter of the legs at the top part
        #----------
        self.cosA = math.cos(math.radians(self.leg_open_angle)) # cos of leg_open_angle
        self.sinA = math.sin(math.radians(self.leg_open_angle)) # sin of leg_open_angle
        self.cosT = math.cos(math.radians(210))                 # cos of 210° of regular polygon separation angle for the legs (0°, 120° and -120°)
        self.sinT = math.sin(math.radians(210))                 # sin of 210° of regular polygon separation angle for the legs (0°, 120° and -120°)
        #----------
        # Camera & lens dimensions
        self.camera_cable       = 20.  # space to leave at the bottom of the table to fold the camera USB cable
        self.camera_body_width  = 37.7 # camera body width (is a square)
        self.camera_body_height = 33.  # camera body height
        self.camera_lens_r      = 15.  # camera lens radius
        self.camera_lens_h      = 41.  # camera lens height
        #----------
        # Table for holding the camera
        self.tables_H                       = 7.   # the width (or height) of the tables bottom & top
        self.bot_table_R                    = 50.  # bottom table radius
        self.top_table_R                    = 40.  # top table radiua
        self.top_table_R_hole               = self.camera_lens_r +1.0 # top table hole radius (where camera lens is holded)
        self.bot_table_cam_hold_wall_width  = 5.   # the width of the wall that holds camera body on the bottom table
        self.bot_table_cam_hold_wall_height = 15.  # the height of the wall that holds camera body on the bottom table
        self.table_top_hole_go_in_lens      = 5.   # how much the table top hole (or ring) goes in the top part of the camera lens
        self.cam_hold_wall_support_width    = 4.   # triangle leg (cross secton) of the camera wall support (bottom table)
        self.cam_hold_wall_support_length   = 0.6*self.camera_body_width # length of the triangle support
        self.pillar_R                       = 3.   # radius of cylindrical pillars holding bottom & top tables (3 pillars)
        self.pillar_position_R              = 32.  # radius of positioning pillars from the Z-axis
        self.alpha_pillar                   =-30.  # rotaion angle in the Z-axis of the 3 pollars to fit better
        #----------
        # height from cone hole at top to ground
        self.Hmax = self.leg_length*self.cosA - self.leg_hole_top - self.legHead_extend/2 
        # camera height (length) is body height + lens height
        self.L_cam = self.camera_body_height + self.camera_lens_h
        # full camera height + USB cable height (needed to fold the cable) 
        self.H_tot_cam = self.L_cam + self.camera_cable
        #---------
        self.top_part   = Part()
        self.legs_part  = Part()
        self.table_part = Part()
        #---------
    # ===============================================
    def Build_top(self, smooth=True):
        """
        This function constructs the top part of the tripod.
        This part is made of a regular triangle fillet vertex
        It has the cone for putting pendulum string and holes
        to attach the legs of the tripod after 3d printing.
        """
        top = RegularPolygon(radius=self.R_top, side_count=3)
        top = fillet(top.vertices(), self.R_fillet_top)
        top = Part() + extrude(top, self.H_top)
        top += Pos(0,0,(self.H_top-self.Cone_top_height)/2)*Rot(180,0,0)*Cone(self.R1_Cone_top+self.Cone_top_width,self.R2_Cone_top+self.Cone_top_width,self.H_top+self.Cone_top_height)
        top -= Pos(0,0,(self.H_top-self.Cone_top_height)/2)*Rot(180,0,0)*Cone(self.R1_Cone_top,self.R2_Cone_top,self.H_top+self.Cone_top_height)
        if smooth:
            top = fillet(top.edges().sort_by(Axis.Z)[4:], 2)
            top = fillet(top.edges().sort_by(Axis.Z)[:2], 0.5)
        # for the legs holes
        topLegHole = Pos(-1.5,0,0)*extrude(Rectangle(self.leg_width+self.legHead_extend+self.tol,self.leg_width+self.legHead_extend+self.tol),-self.leg_hole_top)
        top -= Pos(self.R_legs_top,0,self.leg_hole_top)*topLegHole
        top -= Pos(self.R_legs_top*self.sinT, -self.R_legs_top*self.cosT,self.leg_hole_top)*Rot(0,0,120)*topLegHole
        top -= Pos(self.R_legs_top*self.sinT,self.R_legs_top*self.cosT,self.leg_hole_top)*Rot(0,0,-120)*topLegHole
        return top
    # ===============================================
    def Leg(self,smooth=True):
        """
        This function constructs the leg of the tripod. It is glued at the bottom
        of the top part. It has "head & foot" and a hole to connect the legs from 
        the camera table.
        """
        body_leg = Rectangle(self.leg_width,self.leg_width)-Rectangle(self.leg_width-self.leg_in_width,self.leg_width-self.leg_in_width)
        body_leg = fillet(body_leg.vertices(),self.leg_body_fillet)
        body_leg = Part() + Rot(0,-self.leg_open_angle,0)*extrude(body_leg,-self.leg_length)
        body_leg -= extrude(Rectangle(1.5*self.leg_width,1.5*self.leg_width),self.leg_width*self.sinA)
        body_leg -= Pos(self.leg_length*self.sinA,0,-self.leg_length*self.cosA)*Box(1.5*self.leg_width,1.5*self.leg_width,self.leg_width*self.sinA)
        leg_top = Pos(-1.5,0,0)*extrude(Rectangle(self.leg_width+self.legHead_extend,self.leg_width+self.legHead_extend),-(self.leg_width+2)/2*self.sinA)
        leg_bot = Pos(self.leg_length*self.sinA-1.0,0,-self.leg_length*self.cosA+self.legHead_extend)*Box(self.leg_width+self.legHead_extend,self.leg_width+self.legHead_extend,self.legHead_extend)
        if smooth:
            leg_top = fillet(leg_top.edges().sort_by(Axis.Z)[:8],1)
            leg_bot = fillet(leg_bot.edges().sort_by(Axis.Z)[4:8],4)
            leg_bot = fillet(leg_bot.edges(),1)
        t_leg = self.table_tripod_connection_legs(smooth)
        return Part() + (body_leg + leg_top + leg_bot - Pos(-self.R_legs_top,0,-self.leg_hole_top)*t_leg)
    # ---------------------------------
    def tripod_legs(self,smooth=True):
        """
        This function constructs the three legs of the tripod. It calls the 
        function Leg to construct one leg and the produces two more and
        distribute them in the regular triangle pattern.
        """
        leg_full = self.Leg(smooth)
        leg1 = Pos(self.R_legs_top,0,self.leg_hole_top)*leg_full
        leg2 = Pos(self.R_legs_top*self.sinT,-self.R_legs_top*self.cosT,self.leg_hole_top)*Rot(0, 0, 120)*leg_full
        leg3 = Pos(self.R_legs_top*self.sinT, self.R_legs_top*self.cosT,self.leg_hole_top)*Rot(0, 0, -120)*leg_full
        return Part() + leg1 + leg2 + leg3
    # ===============================================
    def table_Bottom(self, smooth=True):
        """
        This function constructs the bottom part of the camera table. It is
        composed of a disk with three legs that connect to tripod legs and 
        a place with walls and their supports for holdin the camera body. This
        table contains also three "pillars" cyllinders that connect to top table
        to hold it in place.        
        """
        table_bot  = Part() + extrude(Circle(self.bot_table_R), -self.tables_H)
        table_cam  = Part() + Rectangle(self.camera_body_width + self.bot_table_cam_hold_wall_width, self.camera_body_width + self.bot_table_cam_hold_wall_width) 
        table_cam -= Rectangle(self.camera_body_width + self.tol, self.camera_body_width + self.tol)
        table_bot += extrude(table_cam, self.bot_table_cam_hold_wall_height)
        table_bot -= Pos((self.camera_body_width + self.tol)/2, 0, self.bot_table_cam_hold_wall_height/2 + 4) * Box(self.bot_table_cam_hold_wall_width, self.camera_body_width + self.tol, self.bot_table_cam_hold_wall_height)
        cabUSB     = Part() + Pos((self.bot_table_R + self.camera_body_width)/2 -5,0,(self.bot_table_cam_hold_wall_height -self.tables_H)/2) * Box(self.bot_table_R, 2.2 + self.tol, self.tables_H + self.bot_table_cam_hold_wall_height)
        table_bot -= cabUSB
        if smooth:
            table_bot = fillet(table_bot.edges().filter_by(lambda f: f.length >= 2), 1.1)
        #--------------
        rr = Pos(-self.cam_hold_wall_support_length/2, 0, 0)* Rot(90,90,0)*extrude(make_face(Polyline([(0, 0),(0,2*self.cam_hold_wall_support_width ),(self.cam_hold_wall_support_width ,0),(0,0)])),self.cam_hold_wall_support_length)
        XY = (self.camera_body_width + self.bot_table_cam_hold_wall_width)/2
        table_bot += Pos(0, XY, 0) * rr
        table_bot += Rot(0, 0, 90) * Pos(0, XY, 0) * rr
        table_bot += Rot(0, 0, 180) * Pos(0, XY, 0) * rr
        #--------------
        pillar  = Rot(0, 0, self.alpha_pillar)*Pos(0, self.pillar_position_R, 0)*Circle(self.pillar_R)
        pillar += Rot(0, 0, self.alpha_pillar + 120)*Pos(0, self.pillar_position_R, 0)*Circle(self.pillar_R)
        pillar += Rot(0, 0, self.alpha_pillar - 120)*Pos(0, self.pillar_position_R, 0)*Circle(self.pillar_R)
        pillar  = Part() + extrude(pillar, self.L_cam-self.table_top_hole_go_in_lens)
        #--------------
        t_leg1 = self.table_tripod_connection_legs(smooth)
        t_leg2 = Rot(0, 0, 120) * t_leg1
        t_leg3 = Rot(0, 0, -120) * t_leg1
        t_leg  = Part() + t_leg1 + t_leg2 + t_leg3
        return Part()+Rot(0,0,-60)*Pos(0,0,-self.Hmax+self.tables_H+self.camera_cable)*(table_bot + pillar) + t_leg
    # ===============================================
    def table_Top(self, smooth=True):
        """
        This function constructs the top table that holds camera lens. It is a 
        disk with a whole for the lens to enter in. This table is hold via three
        cyllindrical "pillars" extended from the bottom table. 
        """
        table_top = Part() + Pos(0,0,self.L_cam-self.table_top_hole_go_in_lens)*extrude(Circle(self.top_table_R) - Circle(self.top_table_R_hole), self.tables_H)
        if smooth:
            table_top = fillet(table_top.edges(), 1.1)
        return Pos(0,0,-self.Hmax+self.tables_H+self.camera_cable)*table_top
    # ===============================================
    def table(self, smooth=True):
        """
        This function constructs the whole table with the bottom, the top, 
        the pillars and the legs to connect to tripod legs.
        """
        table_top = self.table_Top(smooth)
        table_bot = self.table_Bottom(smooth)
        return table_bot + table_top
    # ===============================================
    def table_tripod_connection_legs(self, smooth=True):
        """
        This function constructs the connection legs between the camera table
        and the tripod legs.
        """
        table_foot_L = 2*((self.Hmax+self.tables_H-self.camera_cable)*self.sinA -self.bot_table_R) + 2
        # table_foot_L = 2*((self.Hmax+self.tables_H-self.camera_cable)*self.sinA - self.leg_hole_top) + 2
        hfoot = 10
        xyfoot = 2
        rr = Plane.YZ * Rectangle(xyfoot * self.tables_H, self.tables_H)
        rr2 = Plane.XZ*Pos(table_foot_L-0.4*hfoot,0,-xyfoot*self.tables_H/2)*Rot(0,0,180+self.leg_open_angle)*RegularPolygon(radius=hfoot,side_count=3)
        obj = extrude(rr, table_foot_L) + extrude(rr2, xyfoot*self.tables_H)
        if smooth:
            obj = fillet(obj.edges().group_by(Axis.X)[1:], 2)
        return Pos(self.bot_table_R,0,-self.Hmax+self.tables_H+self.camera_cable-self.tables_H/2)*obj


#####################################

tr = Tripod()

smooth=False
top = tr.Build_top(smooth)
legs = tr.tripod_legs(smooth)
table = tr.table(smooth)

#####################################

show_object(top, options=dict(alpha=0.))
show_object(legs, options=dict(alpha=0.0,color="red"))
show_object(table, options=dict(alpha=0.,color="cyan"))


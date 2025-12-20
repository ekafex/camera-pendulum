from build123d import *

class ELP_cam:
    """
    Simple vitamin model of the ELP USB camera, for use in assemblies.

    Coordinate system (by construction):
    - Origin: center of the bottom face of the main camera body.
    - +Z: upwards, along the optical axis, towards the lens.
    - +X, +Y: in the plane of the bottom face (square body).
    - Mounting "ears" (bScrew) are along ±Y.
    - Optical axis is along the Z axis at (x=0, y=0).

    All dimensions are in millimetres and approximate the outer envelope
    and key mounting features of the real camera.
    """

    def __init__(self):
        # Main square camera body
        self.baseD = {'x': 37.7, 'y': 37.7, 'z': 33.0}

        # Side mounting block ("ears") with through screw holes
        # x, y, z: block size; h: height offset from bottom; r: screw radius; l: screw length
        self.bScrew = {'x': 8.0, 'y': 2.0, 'z': 9.0, 'h': 3.0, 'r': 2.9, 'l': 6.0}

        # Circular front base (flange) on top of square body
        self.Cbase = {'r': 17.0, 'h': 2.0}

        # Pre-lens ring
        self.pLens = {'r': 14.0, 'h': 2.0}

        # Main lens barrel
        self.Lens  = {'r': 15.0, 'h': 34.0}

        # Lens "middle" thicker ring (focus/iris region)
        # z: offset from pre-lens plane; h: height of this thicker ring
        self.LensM = {'r': 15.8, 'h': 8.6, 'z': 10.0}

        # Small screws on the side of the lens barrel
        # r: radius, h: length; z1, z2: heights above pre-lens base
        self.Lscrew = {'r': 1.6, 'h': 6.0, 'z1': 6.6, 'z2': 26.6}

        # Convenience height: top of pre-lens ring, used as reference for screw Z positions
        self.h_base = self.baseD['z'] + self.Cbase['h'] + self.pLens['h']

        # Reference points/axes that might be useful in assemblies
        self.mount_point = Pos(0, 0, 0)            # bottom center of body
        self.optical_axis = Axis((0, 0, 0), (0, 0, 1))  # along +Z

    def build(self, alpha1: float = 0.0, alpha2: float = 10.0) -> Part:
        """
        Build the ELP camera solid.
        
        Parameters
        ----------
        alpha1, alpha2 : float
            Angles in degrees around the Z axis for the two lens screws,
            measured from +X direction (standard right-handed 3D convention).
        Returns
        -------
        Part
            Combined solid representing the camera body + lens + screw features.
        """

        # 1) Main square body, bottom face at z=0
        base = extrude(
            Sketch() + Rectangle(self.baseD['x'], self.baseD['y']),
            self.baseD['z']
        )

        # 2) Circular front base (flange) on the top of the body
        plane1 = Plane.XY.offset(self.baseD["z"])  # top face of base
        base += extrude(
            Sketch() + plane1 * Circle(self.Cbase['r']),
            self.Cbase['h']
        )

        # 3) Pre-lens ring
        plane2 = Plane.XY.offset(self.baseD["z"]+self.Cbase['h'])  # top of circular base
        pre_lens = extrude(
            Sketch() + plane2 * Circle(self.pLens['r']),
            self.pLens['h']
        )

        # 4) Lens barrel
        plane3 = Plane.XY.offset(self.baseD["z"]+self.Cbase['h']+self.pLens['h'])  # top of pre-lens
        lens = extrude(
            Sketch() + plane3 * Circle(self.Lens['r']),
            self.Lens['h']
        )

        # 5) Thicker mid-lens ring (offset along +Z from pre-lens plane)
        lens += extrude(
            Sketch() + plane3 * Pos(0, 0, self.LensM['z']) * Circle(self.LensM['r']),
            self.LensM['h']
        )

        # 6) Small side screws on the lens barrel
        # Radius where the screw axis sits (outside the lens radius)
        screw_radius = self.Lens['r'] + self.Lscrew['h'] / 2

        lens_screw  = (
            Rot(0, 0, alpha1)
            * Pos(screw_radius, 0, self.h_base + self.Lscrew['z1'])
            * Rot(0, 90, 0)
            * Cylinder(self.Lscrew['r'], self.Lscrew['h'])
        )
        lens_screw += (
            Rot(0, 0, alpha2)
            * Pos(screw_radius, 0, self.h_base + self.Lscrew['z2'])
            * Rot(0, 90, 0)
            * Cylinder(self.Lscrew['r'], self.Lscrew['h'])
        )

        # 7) Side mounting blocks ("ears") with screw holes
        # Positive Y block
        base += extrude(
            Sketch()
            + Pos(0, self.baseD['y'] / 2, self.bScrew['h'])
            * Rectangle(self.bScrew['x'], self.bScrew['y']),
            self.bScrew['z']
        )
        # Negative Y block
        base += (
            Pos(0, -self.baseD['y'] / 2, self.bScrew['h'])
            * extrude(Rectangle(self.bScrew['x'], self.bScrew['y']), self.bScrew['z'])
        )

        # Through holes in blocks
        base -= (
            Pos(0, self.baseD['y'] / 2, self.bScrew['z'] / 2 + self.bScrew['h'])
            * Rot(90, 0, 0)
            * Cylinder(self.bScrew['r'], self.bScrew['l'])
        )
        base -= (
            Pos(0, -self.baseD['y'] / 2, self.bScrew['z'] / 2 + self.bScrew['h'])
            * Rot(90, 0, 0)
            * Cylinder(self.bScrew['r'], self.bScrew['l'])
        )
        
        # USB cable
        l1 = Line((0, 0, 0), (0, -5, 0))
        l2 = JernArc(start=l1 @ 1, tangent=l1 % 1, radius=25, arc_size=-80)
        ln = l1 + l2 
        base += Pos(-self.baseD['x']/2+4.2,0,0)*Rot(90,0,0)*sweep(Plane.XZ*Circle(2.2), path=ln)

        # Final combined solid
        return base + pre_lens + lens + lens_screw
        # return base,pre_lens,lens,lens_screw


# base,pre_lens,lens,lens_screw=ELP_cam().build(alpha1=0, alpha2=30)
# show_object(base,options=dict(alpha=0.,color="black"))
# show_object(pre_lens,options=dict(alpha=0.,color="gray"))
# show_object(lens,options=dict(alpha=0.,color="black"))
# show_object(lens_screw,options=dict(alpha=0.,color="gray"))

# ------------------------------------------------------

# r = ELP_cam().build(alpha1=0, alpha2=30)

# show_object(r,options=dict(alpha=0.))

# ------------------------------------------------------

class Pendulum:
    """
    Vitamin model of a simple 2D pendulum for mechanical assembly
    and visualization purposes.

    Geometry & Coordinate System
    ----------------------------
    - The pivot point is located at the ORIGIN (0, 0, 0).
    - The pendulum string is modeled as a straight cylinder aligned
      along the NEGATIVE Z axis.
      * The string starts at z = 0 (pivot)
      * And ends at z = -L_string

    - The bob is a sphere centered at:
          (0, 0, -L_string)

    - Rotation:
        rotate(theta_x, theta_y)
        produces a rotated copy of the pendulum around the pivot.
        * theta_x rotates around the X axis (tilt in Y–Z plane)
        * theta_y rotates around the Y axis (tilt in X–Z plane)

      This gives two degrees of freedom approximating real pendulum motion.

    Parameters
    ----------
    L_string : float
        Length of the pendulum string in mm.
    D_string : float
        Diameter of the string (cylindrical approximation), in mm.
    R_bob : float
        Radius of the spherical bob in mm.

    Example
    -------
    >>> pend = Pendulum(200, 2, 7)
    >>> r = pend.rotate(theta_x=0, theta_y=20)
    >>> show(r)
    """

    def __init__(self, L_string: float, D_string: float, R_bob: float):
        self.L = L_string
        self.D = D_string
        self.R = R_bob

        # Pre-build the static aligned pendulum model
        self.pend = self._build()

    def _build(self) -> Part:
        """Construct the straight-down pendulum geometry."""
        # String as a cylinder from z=0 to z=-L
        string = extrude(
            Sketch() + Circle(self.D / 2.0),
            amount = -self.L
        )

        # Bob: center at the end of the string
        bob = Pos(0, 0, -self.L) * Sphere(self.R)

        return string + bob

    def rotate(self, theta_x: float = 0.0, theta_y: float = 0.0) -> Part:
        """
        Return a rotated *copy* of the pendulum.

        Parameters
        ----------
        theta_x : float
            Rotation angle about X axis (degrees).
        theta_y : float
            Rotation angle about Y axis (degrees).

        Returns
        -------
        Part
            The rotated pendulum geometry.
        """
        return Rot(theta_x, theta_y, 0) * self.pend


# pendul = Pendulum(200,2,7)
# r = pendul.rotate(30,20)
# show_object(r,options=dict(alpha=0.))








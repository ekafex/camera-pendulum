# assembly_scene.py
from build123d import *
from tripod import Tripod
from elp_camera import ELP_cam, Pendulum


def build_assembly(smooth=True, explode=0.0, pend_angles=(8.0, 12.0)):
    """
    Build a documentation-friendly assembly:
      - tripod top + legs + tables
      - ELP camera
      - pendulum

    explode: 0.0 = normal view
             >0  = exploded offsets (mm) for documentation renders
    """
    tr = Tripod()

    # --- Tripod components (as designed) ---
    top = tr.Build_top(smooth)
    legs = tr.tripod_legs(smooth)
    table = tr.table(smooth)

    # --- Camera vitamin ---
    cam = Part() + ELP_cam().build(alpha1=0, alpha2=30)

    # Place camera so its bottom origin sits on the bottom-table top surface.
    # Bottom table is placed at z = -Hmax + tables_H + camera_cable (see tripod code).
    z_cam_base = -tr.Hmax + tr.tables_H + tr.camera_cable
    cam_loc = Pos(0, 0, z_cam_base)
    cam = cam_loc * Rot(0,0,120)*cam

    # --- Pendulum vitamin ---
    # Put pivot at top center. Top plate spans z=[0, H_top]; choose top surface pivot at z=H_top.
    pivot_z = tr.H_top
    pend = Pendulum(L_string=120.0, D_string=2.0, R_bob=8.0).rotate(*pend_angles)
    pend = Pos(0, 0, pivot_z) * pend

    # --- Exploded view offsets (for figures) ---
    # Keep offsets small and along +Z so it reads cleanly in screenshots.
    top = Pos(0, 0, +explode * 0.0) * top
    legs = Pos(0, 0, -explode * 0.5) * legs
    table = Pos(0, 0, -explode * 1.0) * table
    cam = Pos(0, 0, -explode * 1.2) * cam
    pend = Pos(0, 0, +explode * 0.3) * pend

    return top, legs, table, cam, pend


# if __name__ == "__main__":
smooth = True
# Normal view
top, legs, table, cam, pend = build_assembly(smooth=smooth, explode=0.0)

show_object(top, options=dict(alpha=0.0, color="gold"))
show_object(legs, options=dict(alpha=0.0, color="red"))
show_object(table, options=dict(alpha=0.0))
show_object(cam, options=dict(alpha=0.0, color="black")
)  # semi-transparent to see mount
show_object(pend,options=dict(alpha=0.0, color="black"))

# Optional: exploded “documentation” view
# top, legs, table, cam, pend = build_assembly(smooth=smooth, explode=20.0)
# show_object(top); show_object(legs); show_object(table); show_object(cam); show_object(pend)

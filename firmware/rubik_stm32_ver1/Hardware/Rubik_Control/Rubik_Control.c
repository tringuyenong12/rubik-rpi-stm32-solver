/*
 * Rubik_Control.c
 *
 *  Created on: Oct 27, 2026
 *      Author: phaplun
 */

#include "Rubik_Control.h"

bool Rubik_ScanPrepare(void)
{
    /* Check the last commanded angle before clamping. No position sensors. */
    for (int id = SERVO_ROTATE_FRONT; id <= SERVO_ROTATE_LEFT; ++id)
    {
        const Servo_Rotate_t *rotate = &servo[id].state.rotate;
        float home = rotate->home_angle + rotate->offset_calib_home_angle;
        if (home < 0.0f) home = 0.0f;
        if (home > 180.0f) home = 180.0f;
        if (rotate->current_angle != home) return false;
    }
    for (int id = SERVO_MOVE_FRONT; id <= SERVO_MOVE_LEFT; ++id)
        if (!Servo_Move((Servo_ID_t)id, SERVO_MOVE_CLAMP)) return false;
    return waitUntilServosDone();
}

bool Rubik_ScanQuarter(bool left_right_axis, bool first_clockwise)
{
    const Servo_ID_t first = left_right_axis ? SERVO_ROTATE_LEFT : SERVO_ROTATE_FRONT;
    const Servo_ID_t second = left_right_axis ? SERVO_ROTATE_RIGHT : SERVO_ROTATE_BACK;
    const Servo_ID_t support1 = left_right_axis ? SERVO_MOVE_FRONT : SERVO_MOVE_LEFT;
    const Servo_ID_t support2 = left_right_axis ? SERVO_MOVE_BACK : SERVO_MOVE_RIGHT;
    const Servo_ID_t grip1 = (Servo_ID_t)(first + SERVO_MOVE_FRONT);
    const Servo_ID_t grip2 = (Servo_ID_t)(second + SERVO_MOVE_FRONT);
    const Servo_Rotate_Position_t cw = SERVO_ROTATE_CLOCKWISE;
    const Servo_Rotate_Position_t ccw = SERVO_ROTATE_ANTICLOCKWISE;

    /* Keep one pair on the cube throughout each handoff. */
    return Servo_Move(grip1, SERVO_MOVE_TIGHT_CLAMP)
        && Servo_Move(grip2, SERVO_MOVE_TIGHT_CLAMP) && waitUntilServosDone()
        && Servo_Move(support1, SERVO_MOVE_FULL_RELEASE)
        && Servo_Move(support2, SERVO_MOVE_FULL_RELEASE) && waitUntilServosDone()
        && Servo_Rotate(first, first_clockwise ? cw : ccw)
        && Servo_Rotate(second, first_clockwise ? ccw : cw) && waitUntilServosDone()
        && Servo_Move(support1, SERVO_MOVE_CLAMP)
        && Servo_Move(support2, SERVO_MOVE_CLAMP) && waitUntilServosDone()
        && Servo_Move(grip1, SERVO_MOVE_FULL_RELEASE)
        && Servo_Move(grip2, SERVO_MOVE_FULL_RELEASE) && waitUntilServosDone()
        && Servo_Rotate(first, SERVO_ROTATE_HOME)
        && Servo_Rotate(second, SERVO_ROTATE_HOME) && waitUntilServosDone()
        && Servo_Move(grip1, SERVO_MOVE_CLAMP)
        && Servo_Move(grip2, SERVO_MOVE_CLAMP) && waitUntilServosDone();
}
#include "main.h"

// L, R, U, D, F, B         Quay chieu kim dong ho
// L_, R_, U_, D_, F_, B_   Quay nguoc chieu kim dong ho


// Cac trang thai ban dau truoc khi thuc hien tung lenh xoay Rubik, thi phai deu dang o
//  mot trang thai ban dau, la cac Rubik Rotate phai dang o Home_Angle,
// va cac Rubik Move phai dang kep la Clamp_Angle.


void Rubik_Hold_Start_Position(void){
   Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
   Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
   Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
   Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);

   Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
   Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
   HAL_Delay(5000);

   Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
   Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
   waitUntilServosDone();



}


void Rubik_Release(void){
    // Rut arm trai va phai ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

    // Rut arm truoc va sau ra
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();

    // Dua tat ca cac arm ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);

    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    HAL_Delay(5000);

    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();
}


 void Rubik_Left(){
    // Xoay mat ben trai cua Rubik theo chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Rut arm trai ra, de mat ben trai cua Rubik tro ve trang thai ban dau
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_FULL_RELEASE);
    waitUntilServosDone();
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Dua arm trai ve trang thai ban dau
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();
 }

void Rubik_Left_(){
    // Xoay mat ben trai cua Rubik nguoc chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Rut arm trai ra, de mat ben trai cua Rubik tro ve trang thai ban dau
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_FULL_RELEASE);
    waitUntilServosDone();
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Dua arm trai ve trang thai ban dau
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();
 }

 void Rubik_Right(){
    // Xoay mat ben phai cua Rubik theo chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Rut arm phai ra, de mat ben phai cua Rubik tro ve trang thai ban dau
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_FULL_RELEASE);
    waitUntilServosDone();
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Dua arm phai ve trang thai ban dau
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();
 }

 void Rubik_Right_(){
    // Xoay mat ben phai cua Rubik nguoc chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Rut arm phai ra, de mat ben phai cua Rubik tro ve trang thai ban dau
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_FULL_RELEASE);
    waitUntilServosDone();
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Dua arm phai ve trang thai ban dau
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();
 }


 void Rubik_Front(){
    // Xoay mat ben truoc cua Rubik theo chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Rut arm truoc ra, de mat ben truoc cua Rubik tro ve trang thai ban dau
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_FULL_RELEASE);
    waitUntilServosDone();
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Dua arm truoc ve trang thai ban dau
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();
 }

 void Rubik_Front_(){
    // Xoay mat ben truoc cua Rubik nguoc chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Rut arm truoc ra, de mat ben truoc cua Rubik tro ve trang thai ban dau
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_FULL_RELEASE);
    waitUntilServosDone();
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Dua arm truoc ve trang thai ban dau
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();
 }

 void Rubik_Back(){
    // Xoay mat ben sau cua Rubik theo chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Rut arm sau ra, de mat ben sau cua Rubik tro ve trang thai ban dau
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_FULL_RELEASE);
    waitUntilServosDone();
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Dua arm sau ve trang thai ban dau
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    waitUntilServosDone();
 }

 void Rubik_Back_(){
    // Xoay mat ben sau cua Rubik nguoc chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Rut arm sau ra, de mat ben sau cua Rubik tro ve trang thai ban dau
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_FULL_RELEASE);
    waitUntilServosDone();
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Dua arm sau ve trang thai ban dau
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    waitUntilServosDone();
 }

 void Rubik_UpToFront(){
    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_TIGHT_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_TIGHT_CLAMP);
    // Rut arm FRONT va BACK ra, de chuan bi xoay Rubik tu Up xuong Front
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();

    // Xoay mat ben tren cua Rubik xuong mat ben truoc theo nguoc chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_CLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Co dinh arm FRONT va BACK
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

    // Rut arm trai va phai ra
    // Rut arm LEFT va RIGHT ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

    // Xoay mat Front
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_TIGHT_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_TIGHT_CLAMP);

    // Rut arm Front va Back ra
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();


    // Xoay rubik tu mat FRONT len mat UP
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_ANTICLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_CLOCKWISE);

        // Xoay arm FRONT va BACK ve goc xoay ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

        // Rut arm trai va phai ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

        // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);

    waitUntilServosDone();
 }



 void Rubik_Up_ToFront(){
    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_TIGHT_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_TIGHT_CLAMP);
    // Rut arm FRONT va BACK ra, de chuan bi xoay Rubik tu Up xuong Front
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();

    // Xoay mat ben tren cua Rubik xuong mat ben truoc theo nguoc chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_CLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Co dinh arm FRONT va BACK
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

    // Rut arm trai va phai ra
    // Rut arm LEFT va RIGHT ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

    // Xoay mat Front
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_TIGHT_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_TIGHT_CLAMP);

    // Rut arm Front va Back ra
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();


    // Xoay rubik tu mat FRONT len mat UP
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_ANTICLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_CLOCKWISE);

        // Xoay arm FRONT va BACK ve goc xoay ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

        // Rut arm trai va phai ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

        // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);

    waitUntilServosDone();
 }


 void Rubik_DownToFront(){
    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_TIGHT_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_TIGHT_CLAMP);
    // Rut arm FRONT va BACK ra, de chuan bi xoay Rubik tu Down lên Front
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();

    // Xoay mat ben duoi cua Rubik len mat ben truoc theo nguoc chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_ANTICLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Co dinh arm FRONT va BACK
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

    // Rut arm trai va phai ra
    // Rut arm LEFT va RIGHT ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

    // Xoay mat Front
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_TIGHT_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_TIGHT_CLAMP);

    // Rut arm Front va Back ra
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();


    // Xoay rubik tu mat FRONT xuong mat DOwn
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_CLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_ANTICLOCKWISE);

        // Xoay arm FRONT va BACK ve goc xoay ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

        // Rut arm trai va phai ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

        // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);

    waitUntilServosDone();
 }


 void Rubik_Down_ToFront(){
    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_TIGHT_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_TIGHT_CLAMP);
    // Rut arm FRONT va BACK ra, de chuan bi xoay Rubik tu Down lên Front
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();

    // Xoay mat ben duoi cua Rubik len mat ben truoc theo nguoc chieu kim dong ho
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_ANTICLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Co dinh arm FRONT va BACK
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

    // Rut arm trai va phai ra
    // Rut arm LEFT va RIGHT ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

    // Xoay mat Front
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_TIGHT_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_TIGHT_CLAMP);

    // Rut arm Front va Back ra
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();


    // Xoay rubik tu mat FRONT xuong mat DOwn
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_CLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_ANTICLOCKWISE);

        // Xoay arm FRONT va BACK ve goc xoay ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

        // Rut arm trai va phai ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

        // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);

    waitUntilServosDone();
 }



 void Rubik_Front_Back_Move_Full_Release(){
    // Rut arm FRONT va BACK ra
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_FULL_RELEASE);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_FULL_RELEASE);
    return;

 }

  void Rubik_Left_Right_Move_Full_Release(){
      // Rut arm LEFT va RIGHT ra
      Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_FULL_RELEASE);
      Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_FULL_RELEASE);   
      return;
 }

void Rubik_LR(){
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_CLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Rut arm trai va phai ra
    // Rut arm LEFT va RIGHT ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

        // Kep chat hai mat trai va phai cua Rubik
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();

    return;
}

void Rubik_LR_(){
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_CLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Rut arm trai va phai ra
    // Rut arm LEFT va RIGHT ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();


    return;
}

void Rubik_L_R(){
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_ANTICLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Rut arm trai va phai ra
    // Rut arm LEFT va RIGHT ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    return;
}

void Rubik_L_R_(){
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_ANTICLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Rut arm trai va phai ra
    // Rut arm LEFT va RIGHT ra
    Rubik_Left_Right_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm trai va phai ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    return;
}

void Rubik_FB(){
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_CLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Rut arm truoc va sau ra
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm truoc va sau ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    waitUntilServosDone();
    return;
}

void Rubik_FB_(){
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_CLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Rut arm truoc va sau ra
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm truoc va sau ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    return;
}


void Rubik_F_B(){
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_ANTICLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_CLOCKWISE);
    waitUntilServosDone();

    // Rut arm truoc va sau ra
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm truoc va sau ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    waitUntilServosDone();
    return;
}


void Rubik_F_B_(){
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_ANTICLOCKWISE);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_ANTICLOCKWISE);
    waitUntilServosDone();

    // Rut arm truoc va sau ra
    Rubik_Front_Back_Move_Full_Release();
    waitUntilServosDone();

    // Xoay arm truoc va sau ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    waitUntilServosDone();
    return;
}



void Rubik_Reset(void){
    // Dua tat ca cac arm ve trang thai ban dau
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_FULL_RELEASE);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_FULL_RELEASE);
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_FULL_RELEASE);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_FULL_RELEASE);

    waitUntilServosDone();

    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);


    waitUntilServosDone();
}

void Rubik_Prepare(void){   // Đưa Rubik về trạng thái chuẩn bị để thực hiện các lệnh xoay Rubik
    // Dua tat ca cac arm ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);
    waitUntilServosDone();

    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
    waitUntilServosDone();
}


void Rubik_Put(void){ // Đưa các cánh tay về trạng thái đặt Rubik để người đưa hoặc lấy Rubik ra khỏi máy
    // Dua tat ca cac arm ve trang thai ban dau
    Servo_Rotate(SERVO_ROTATE_FRONT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_RIGHT, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_BACK, SERVO_ROTATE_HOME);
    Servo_Rotate(SERVO_ROTATE_LEFT, SERVO_ROTATE_HOME);

    waitUntilServosDone();
    Servo_Move(SERVO_MOVE_FRONT, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_BACK, SERVO_MOVE_CLAMP);
    Servo_Move(SERVO_MOVE_RIGHT, SERVO_MOVE_CLAMP);
        Servo_Move(SERVO_MOVE_LEFT, SERVO_MOVE_FULL_RELEASE);

    waitUntilServosDone();
}
















 

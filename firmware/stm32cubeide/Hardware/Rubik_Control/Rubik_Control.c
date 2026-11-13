/*
 * Rubik_Control.c
 *
 *  Created on: Oct 27, 2026
 *      Author: phaplun
 */

#include "Rubik_Control.h"
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

    // Xoay mat Front nguoc chieu kim dong ho cho U'
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

    // Xoay mat Front nguoc chieu kim dong ho cho U'
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



















 

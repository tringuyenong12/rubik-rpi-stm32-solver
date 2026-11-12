#include <stdlib.h>
#include <stdio.h>
#include "Rubik_Control.h"
void HAL_Delay(uint32_t delay_ms) { (void)delay_ms; }
static void check(bool condition)
{
    if (!condition) {
        fputs("Motion invariant failed.\n", stderr);
        exit(EXIT_FAILURE);
    }
}
static Servo_Move_Position_t move[4];
static Servo_Rotate_Position_t rotate[4];
static int first_tilt;
static void check_hold(void)
{
    unsigned held=0;
    for (unsigned i=0;i<4;++i) held += move[i]==SERVO_MOVE_CLAMP || move[i]==SERVO_MOVE_TIGHT_CLAMP;
    check(held>=2);
}
bool Servo_Move(Servo_ID_t id, Servo_Move_Position_t p)
{ check(id>=4 && id<8); move[id-4]=p; check_hold(); return true; }
bool Servo_Rotate(Servo_ID_t id, Servo_Rotate_Position_t p)
{
    check(id>=0 && id<4); check_hold();
    if (id==SERVO_ROTATE_LEFT && p!=SERVO_ROTATE_HOME && first_tilt<0) first_tilt=p;
    rotate[id]=p; return true;
}
bool waitUntilServosDone(void) {check_hold(); return true;}
int main(void)
{
    void (*fn[])(void)={Rubik_Left,Rubik_Left_,Rubik_Right,Rubik_Right_,Rubik_Front,Rubik_Front_,Rubik_Back,Rubik_Back_,Rubik_UpToFront,Rubik_Up_ToFront,Rubik_DownToFront,Rubik_Down_ToFront};
    for (unsigned n=0;n<12;++n) {
        for(unsigned i=0;i<4;++i) {move[i]=SERVO_MOVE_CLAMP;rotate[i]=SERVO_ROTATE_HOME;}
        fprintf(stderr, "Checking move %u\n", n);
        first_tilt=-1; fn[n]();
        for(unsigned i=0;i<4;++i) {check(move[i]==SERVO_MOVE_CLAMP);check(rotate[i]==SERVO_ROTATE_HOME);}
        if(n>=8) check(first_tilt==(n<10?SERVO_ROTATE_CLOCKWISE:SERVO_ROTATE_ANTICLOCKWISE));
    }
    puts("Rubik moves: valid servo types, cube held and HOME/CLAMP restored for all 12 quarter turns.");
}

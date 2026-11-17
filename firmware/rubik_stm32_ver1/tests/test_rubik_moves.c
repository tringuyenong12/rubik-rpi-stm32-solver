#include <assert.h>
#include <stdio.h>
#include "Rubik_Control.h"
static Servo_Move_Position_t move[4];
static Servo_Rotate_Position_t rotate[4];
static int first_tilt;
static void check_hold(void)
{
    unsigned held=0;
    for (unsigned i=0;i<4;++i) held += move[i]==SERVO_MOVE_CLAMP || move[i]==SERVO_MOVE_TIGHT_CLAMP;
    assert(held>=2);
}
bool Servo_Move(Servo_ID_t id, Servo_Move_Position_t p)
{ assert(id>=4 && id<8); move[id-4]=p; check_hold(); return true; }
bool Servo_Rotate(Servo_ID_t id, Servo_Rotate_Position_t p)
{
    assert(id>=0 && id<4); check_hold();
    if (id==SERVO_ROTATE_LEFT && p!=SERVO_ROTATE_HOME && first_tilt<0) first_tilt=p;
    rotate[id]=p; return true;
}
bool waitUntilServosDone(void) {check_hold(); return true;}
int main(void)
{
    void (*fn[])(void)={Left,Left_,Right,Right_,Front,Front_,Back,Back_,UpToFront,Up_ToFront,DownToFront,Down_ToFront};
    for (unsigned n=0;n<12;++n) {
        for(unsigned i=0;i<4;++i) {move[i]=SERVO_MOVE_CLAMP;rotate[i]=SERVO_ROTATE_HOME;}
        first_tilt=-1; fn[n]();
        for(unsigned i=0;i<4;++i) {assert(move[i]==SERVO_MOVE_CLAMP);assert(rotate[i]==SERVO_ROTATE_HOME);}
        if(n>=8) assert(first_tilt==(n<10?SERVO_ROTATE_CLOCKWISE:SERVO_ROTATE_ANTICLOCKWISE));
    }
    puts("Rubik moves: valid servo types, cube held and HOME/CLAMP restored for all 12 quarter turns.");
}

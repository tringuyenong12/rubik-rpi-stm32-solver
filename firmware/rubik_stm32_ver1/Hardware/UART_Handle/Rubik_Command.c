/*
 * Rubik_Command.c
 *
 *  Created on: Nov 15, 2026
 *      Author: Dell
 */


#include "Rubik_Command.h"
#include "../Rubik_Control/Rubik_Control.h"
#include <string.h>


//#<ID> RUBIK PING
//#<ID> RUBIK RESET
//#<ID> RUBIK MOVE <face> <duration_ms>
//#<ID> RUBIK STOP

enum { RUBIK_UNKNOWN, RUBIK_PING, RUBIK_RESET, RUBIK_MOVE, RUBIK_STOP, RUBIK_PREPARE, RUBIK_PUT };


void Rubik_CommandHandler(uint8_t argc, char *argv[], uint16_t command_id)
{

    if (argc < 3U)
    {
         UART_Error(command_id, "BAD_ARG");
         return;
     }
    const char *action = argv[2];
    int code = RUBIK_UNKNOWN;
    if (strcmp(action, "PING") == 0) code = RUBIK_PING;
    else if (strcmp(action, "RESET") == 0) code = RUBIK_RESET;
    else if (strcmp(action, "MOVE") == 0) code = RUBIK_MOVE;
    else if (strcmp(action, "STOP") == 0) code = RUBIK_STOP;
    else if (strcmp(action, "PREPARE") == 0) code = RUBIK_PREPARE;
    else if (strcmp(action, "PUT") == 0) code = RUBIK_PUT;

     switch (code)
     {
     case RUBIK_MOVE:
     {
              if (argc < 4U || argc > 5U)
              { UART_Error(command_id, "BAD_ARG"); return; }
    	 	  const char *move = argv[3];

              int pair = 0;
              if (strcmp(move, "LR") == 0) pair = 1;
              else if (strcmp(move, "LR_") == 0) pair = 2;
              else if (strcmp(move, "L_R") == 0) pair = 3;
              else if (strcmp(move, "L_R_") == 0) pair = 4;
              else if (strcmp(move, "FB") == 0) pair = 5;
              else if (strcmp(move, "FB_") == 0) pair = 6;
              else if (strcmp(move, "F_B") == 0) pair = 7;
              else if (strcmp(move, "F_B_") == 0) pair = 8;

              if (pair != 0)
              {
                  UART_Accept(command_id);
                  switch (pair)
                  {
                  case 1:
                      Rubik_LR();
                      break;
                  case 2:
                      Rubik_LR_();
                      break;
                  case 3:
                      Rubik_L_R();
                      break;
                  case 4:
                      Rubik_L_R_();
                      break;
                    case 5:
                        Rubik_FB();
                        break;
                    case 6:
                        Rubik_FB_();
                        break;  
                    case 7:
                        Rubik_F_B();
                        break;  
                    case 8:
                        Rubik_F_B_();
                        break;
                        
                  default:
                      break;
                  }
                  UART_Done(command_id);
                  break;
              }

    	      if (strcmp(move, "L") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_Left();
    	          UART_Done(command_id);
    	      }
    	      else if (strcmp(move, "R") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_Right();
    	          UART_Done(command_id);

    	      }
    	      else if (strcmp(move, "U") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_UpToFront();
    	          UART_Done(command_id);

    	      }
    	      else if (strcmp(move, "D") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_DownToFront();
    	          UART_Done(command_id);

    	      }
    	      else if (strcmp(move, "F") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_Front();
    	          UART_Done(command_id);

    	      }
    	      else if (strcmp(move, "B") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_Back();
    	          UART_Done(command_id);

    	      }
    	      else if (strcmp(move, "L_") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_Left_();
    	          UART_Done(command_id);

    	      }
    	      else if (strcmp(move, "R_") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_Right_();
    	          UART_Done(command_id);

    	      }
    	      else if (strcmp(move, "U_") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_Up_ToFront();
    	          UART_Done(command_id);

    	      }
    	      else if (strcmp(move, "D_") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_Down_ToFront();
    	          UART_Done(command_id);

    	      }
    	      else if (strcmp(move, "F_") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_Front_();
    	          UART_Done(command_id);

    	      }
    	      else if (strcmp(move, "B_") == 0)
    	      {
    	    	  UART_Accept(command_id);
    	          Rubik_Back_();
    	          UART_Done(command_id);
    	      }
    	      else {
    	    	  UART_Error(command_id, "BAD_RUBIK_MOVE_ARG");
    	      }
    	      break;
     }
     case RUBIK_PING:
         if (argc != 3U) { UART_Error(command_id, "BAD_ARG"); return; }
         UART_Accept(command_id);
         UART_Done(command_id);
         break;
     case RUBIK_RESET:
         if (argc != 3U) { UART_Error(command_id, "BAD_ARG"); return; }
         UART_Accept(command_id);
         Rubik_Reset();
         UART_Done(command_id);
         break;
     case RUBIK_STOP:
         if (argc != 3U) { UART_Error(command_id, "BAD_ARG"); return; }
         UART_Command_Stop(command_id);
         break;
    case RUBIK_PREPARE:
         if (argc != 3U) { UART_Error(command_id, "BAD_ARG"); return; }
         UART_Accept(command_id);
         Rubik_Prepare();
         UART_Done(command_id);
         break;
    case RUBIK_PUT:
         if (argc != 3U) { UART_Error(command_id, "BAD_ARG"); return; }
         UART_Accept(command_id);
         Rubik_Put();
         UART_Done(command_id);
         break;
     default:
         UART_Error(command_id, "UNKNOWN_CMD");
         break;
     }
}

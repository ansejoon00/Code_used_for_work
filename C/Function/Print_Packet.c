#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

bool DEBUG = true;

void printf_byte(const char *label, uint8_t byte_val)
{
    if (DEBUG)
    {
        printf("  [%s] [1]\n", label);
        printf("     %02X\n", byte_val);
    }
}

void printf_bytes(const char *label, const uint8_t *array, int start_index, int size)
{
    if (DEBUG)
    {
        printf("  [%s] [%d]", label, size);
        for (int i = 0; i < size; i++)
        {
            if (i % 25 == 0)
                printf("\n    ");
            printf(" %02X", array[start_index + i]);
        }
        printf("\n");
    }
}

void printf_bytes_s(const char *label, const uint8_t *array, int start_index, int size)
{
    printf("  [%s] [%d]", label, size);
    for (int i = 0; i < size; i++)
    {
        if (i % 25 == 0)
            printf("\n    ");
        printf(" %02X", array[start_index + i]);
    }
    printf("\n");
}

void printf_send_packet(const uint8_t *packet, int size)
{
    printf("[Send Packet Data Size] : %d\n", size);
    printf_bytes_s("Send Packet Data", packet, 0, size);
}

void printf_trap_packet(const uint8_t *packet, int size)
{
    printf("[Trap Packet Data Size] : %d\n", size);
    printf_bytes_s("Trap Packet Data", packet, 0, size);
}

void printf_recv_packet(const uint8_t *packet, int size)
{
    printf("[Recv Packet Data Size] : %d\n", size);
    printf_bytes_s("Recv Packet Data", packet, 0, size);
}

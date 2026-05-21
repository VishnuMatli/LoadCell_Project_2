#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/stat.h>
#include <stdint.h>
#include <errno.h>

#define SERVER_IP "127.0.0.1"
#define SERVER_PORT 9999
#define FILENAME_LENGTH_BYTES 4
#define FILE_CONTENT_LENGTH_BYTES 8
#define MAX_FILENAME_LENGTH 255

// Function to convert 64-bit value from big-endian to host byte order
static uint64_t be64toh_custom(uint64_t val) {
    if (__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__) {
        return __builtin_bswap64(val);
    }
    return val;
}

// Function to convert 32-bit value from big-endian to host byte order
static uint32_t be32toh_custom(uint32_t val) {
    if (__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__) {
        return __builtin_bswap32(val);
    }
    return val;
}

// Function to receive data of a specific size
int recv_all(int sockfd, void *buffer, size_t len) {
    size_t total = 0;
    size_t bytes_left = len;
    ssize_t n;
    while (total < len) {
        n = recv(sockfd, buffer + total, bytes_left, 0);
        if (n <= 0) {
            return -1;
        }
        total += n;
        bytes_left -= n;
    }
    return 0;
}

// Function to read a file length from the socket
static int read_file_length(int sockfd, uint64_t* length_out, size_t bytes_to_read) {
    uint64_t length_network = 0;
    if (recv_all(sockfd, &length_network, bytes_to_read) != 0) {
        return -1;
    }

    if (bytes_to_read == FILENAME_LENGTH_BYTES) {
        *length_out = be32toh_custom((uint32_t)length_network);
    } else if (bytes_to_read == FILE_CONTENT_LENGTH_BYTES) {
        *length_out = be64toh_custom(length_network);
    }
    
    return 0;
}

// Main function to receive files from server
void receive_files(int sockfd) {
    char *filename = NULL;
    char *filepath = NULL;
    char *file_content = NULL;

    // Create recv_data directory if it doesn't exist
    mkdir("recv_data", 0777);

    // Read the total number of files to expect
    uint32_t num_files_network;
    if (recv_all(sockfd, &num_files_network, sizeof(uint32_t)) != 0) {
        fprintf(stderr, "[CLIENT] Error: Failed to receive number of files.\n");
        return;
    }
    uint32_t num_files = be32toh_custom(num_files_network);
    printf("[CLIENT] Expecting to receive %u files.\n", num_files);

    for (uint32_t i = 0; i < num_files; ++i) {
        uint64_t filename_length;
        if (read_file_length(sockfd, &filename_length, FILENAME_LENGTH_BYTES) != 0) {
            fprintf(stderr, "[CLIENT] Connection closed or error while receiving filename length.\n");
            break;
        }

        if (filename_length > MAX_FILENAME_LENGTH) {
            fprintf(stderr, "[CLIENT] Error: Received filename length (%lu) exceeds max allowed (%u).\n", (unsigned long)filename_length, MAX_FILENAME_LENGTH);
            break;
        }

        filename = malloc(filename_length + 1);
        if (!filename) {
            fprintf(stderr, "[CLIENT] Error: Failed to allocate memory for filename.\n");
            break;
        }
        filename[filename_length] = '\0';

        if (recv_all(sockfd, filename, filename_length) != 0) {
            fprintf(stderr, "[CLIENT] Connection closed or error while receiving filename.\n");
            free(filename);
            break;
        }

        printf("[CLIENT] Received filename: %s\n", filename);

        uint64_t file_content_length;
        if (read_file_length(sockfd, &file_content_length, FILE_CONTENT_LENGTH_BYTES) != 0) {
            fprintf(stderr, "[CLIENT] Connection closed or error while receiving file content length.\n");
            free(filename);
            break;
        }

        if (file_content_length > 0) {
            file_content = malloc(file_content_length);
            if (!file_content) {
                fprintf(stderr, "[CLIENT] Error: Failed to allocate memory for file content.\n");
                free(filename);
                break;
            }

            if (recv_all(sockfd, file_content, file_content_length) != 0) {
                fprintf(stderr, "[CLIENT] Connection closed or error while receiving file content.\n");
                free(filename);
                free(file_content);
                break;
            }

            filepath = malloc(strlen("recv_data/") + strlen(filename) + 1);
            if (filepath) {
                sprintf(filepath, "recv_data/%s", filename);
                FILE *fp = fopen(filepath, "w");
                if (fp) {
                    fwrite(file_content, 1, file_content_length, fp);
                    fclose(fp);
                    printf("[CLIENT] Saved file: %s (%lu bytes)\n", filepath, (unsigned long)file_content_length);
                } else {
                    perror("Error saving file");
                }
                free(filepath);
            }
            free(file_content);
        } else {
            printf("[CLIENT] File %s has no content.\n", filename);
        }
        free(filename);
    }
}

int main(void) {
    int sockfd;
    struct sockaddr_in serv_addr;

    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("Error creating socket");
        return 1;
    }

    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(SERVER_PORT);

    if (inet_pton(AF_INET, SERVER_IP, &serv_addr.sin_addr) <= 0) {
        perror("Invalid server IP address");
        close(sockfd);
        return 1;
    }

    if (connect(sockfd, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        perror("Error connecting to server");
        close(sockfd);
        return 1;
    }

    printf("[CLIENT] Connected to server.\n");

    receive_files(sockfd);

    close(sockfd);
    printf("[CLIENT] Connection closed.\n");

    return 0;
}

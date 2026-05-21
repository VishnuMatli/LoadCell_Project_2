#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <stdint.h>

#define SERVER_IP   "127.0.0.1"
#define SERVER_PORT 5000
#define OUTPUT_FOLDER "client_files"
#define BUFFER_SIZE 4096

ssize_t recv_all(int sockfd, void *buffer, size_t len) {
    size_t total = 0;
    while (total < len) {
        ssize_t n = recv(sockfd, (char*)buffer + total, len - total, 0);
        if (n <= 0) return -1;
        total += n;
    }
    return total;
}

uint32_t recv_uint32(int sockfd) {
    unsigned char buf[4];
    if (recv_all(sockfd, buf, 4) != 4) return 0;
    return (buf[0]<<24) | (buf[1]<<16) | (buf[2]<<8) | buf[3];
}

uint64_t recv_uint64(int sockfd) {
    unsigned char buf[8];
    if (recv_all(sockfd, buf, 8) != 8) return 0;
    uint64_t value = 0;
    for (int i=0; i<8; i++) {
        value = (value<<8) | buf[i];
    }
    return value;
}

int main() {
    int sockfd;
    struct sockaddr_in server_addr;

    system("mkdir -p " OUTPUT_FOLDER);

    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) { perror("socket"); exit(1); }

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(SERVER_PORT);
    inet_pton(AF_INET, SERVER_IP, &server_addr.sin_addr);

    if (connect(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("connect");
        exit(1);
    }

    printf("[CLIENT] Connected to server %s:%d\n", SERVER_IP, SERVER_PORT);

    for (uint32_t index = 0; ; index++) {
        // Send index
        uint32_t index_be = htonl(index);
        if (send(sockfd, &index_be, 4, 0) != 4) {
            perror("send index");
            break;
        }

        // Receive filename length
        uint32_t filename_len = recv_uint32(sockfd);
        if (filename_len == 0) {
            printf("[CLIENT] No more files.\n");
            break;
        }

        char *filename = malloc(filename_len + 1);
        recv_all(sockfd, filename, filename_len);
        filename[filename_len] = '\0';

        uint64_t file_size = recv_uint64(sockfd);

        char filepath[512];
        snprintf(filepath, sizeof(filepath), OUTPUT_FOLDER"/%s", filename);

        FILE *fp = fopen(filepath, "wb");
        if (!fp) { perror("fopen"); free(filename); break; }

        printf("[CLIENT] Receiving file %u: '%s' (%llu bytes)\n",
               index, filename, (unsigned long long)file_size);

        char buffer[BUFFER_SIZE];
        uint64_t received = 0;
        while (received < file_size) {
            size_t to_read = (file_size - received > BUFFER_SIZE) ? BUFFER_SIZE : (size_t)(file_size - received);
            ssize_t n = recv(sockfd, buffer, to_read, 0);
            if (n <= 0) { perror("recv file data"); break; }
            fwrite(buffer, 1, n, fp);
            received += n;
        }

        fclose(fp);
        free(filename);

        printf("[CLIENT] Saved '%s'\n", filepath);
    }

    close(sockfd);
    return 0;
}

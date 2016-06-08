#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define EXPORT __attribute__((visibility("default")))

#define LONG uint32_t
#define BYTE uint8_t
#define FALSE 0 
#define TRUE 1

#define RIGHT 1
#define LEFT 3

#define SMOOTH_SIZE 20

typedef struct {
    int x;
    int y;
    BYTE dir;
} BorderPoint;

typedef struct {
    int width;
    int height;
    LONG *img;
    LONG *orig_img;
    float *dist;
} XYData;

inline LONG adjust_pixel(LONG pixel, int amount) {
    for (int i=0; i<24; i+=8) {
        LONG mask = 0xff << i;
        LONG val = (pixel & mask) >> i;
        if (amount<0 && val < (unsigned int)(-amount)) {
            val=0;
        }
        else {
            val += amount;
            if (val>0xff) val=0xff;
        }
        // replace component by val
        pixel = (pixel & (~mask)) | (val << i);
    }
    return pixel;
}

inline int getdx(int dir) {
    dir = dir % 4;
    // in:  0  1  2  3
    // out: 1  0 -1  0
    return (dir%2) ? 0 : (1-dir);
}

inline int getdy(int dir) {
    dir = dir % 4;
    // in:  0  1  2  3
    // out: 0  1  0 -1 
    return (dir%2) ? (2-dir) : 0;
}

int out_of_bounds(XYData xydata, int idx) {
    if (idx<0 || idx>=xydata.width*xydata.height) return TRUE;
    return FALSE;
}

LONG img_safe(XYData xydata, int x, int y) {
    int idx = y*xydata.width + x;
    if (out_of_bounds(xydata, idx)) return 0;
    return xydata.img[idx];
}

BorderPoint find_start(XYData xydata) {
    BorderPoint result;
    result.x = xydata.width/2;
    result.y = 0;
    // start point will be pointing right
    result.dir = 0;
    
    // search starting point from the top center downwards.
    while ((img_safe(xydata, result.x, result.y) & 0xff000000) == 0) {
        result.y++;
        if (result.y>=xydata.height) {
            result.x = -1;
            return result;
        }
    }
    return result;
}

BorderPoint move_to_next(XYData xydata, BorderPoint cursor) {
    // Step to find next pixel
    int found_next = FALSE;
    // count consecutive right turns
    
    int p1x = cursor.x + getdx(cursor.dir)+getdx(cursor.dir+LEFT);
    int p1y = cursor.y + getdy(cursor.dir)+getdy(cursor.dir+LEFT);
    
    
    int idx = p1y*xydata.width + p1x;
    if (!out_of_bounds(xydata, idx)) {
        if ((img_safe(xydata, p1x, p1y) & 0xff000000) != 0) {
            // p1 is the next point
            cursor.x = p1x;
            cursor.y = p1y;
            cursor.dir = (cursor.dir + LEFT) % 4;
            found_next = TRUE;
            //printf("->go, LEFT\n");
        }
    }
    if (!found_next) {
        // p1 was transparent, check p2
        int p2x = cursor.x + getdx(cursor.dir);
        int p2y = cursor.y + getdy(cursor.dir);
        idx = p2y*xydata.width + p2x;
        //printf("-> p2=%i %i ", p2x, p2y);
        if (!out_of_bounds(xydata, idx)) {
            if ((img_safe(xydata, p2x, p2y) & 0xff000000) != 0) {
                // p2 is the next point
                cursor.x = p2x;
                cursor.y = p2y;
                // do not turn
                found_next = TRUE;
                // printf("->go\n");
            }
        }
    }
    if (!found_next) {
        // p1 and p2 transparent => turn RIGHT and try again
        cursor.dir = (cursor.dir + RIGHT) % 4;
        // printf("-> RIGHT\n");
        // Note that there is no check for >n consecutive right turns. That is because after 4 right turns
        // cursor will be back in the initial state, and thus the main proc will enter next stage or exit.
        // Also the single pixel case is not really likely.
    }
    return cursor;
}

void init_dist_and_origimg(XYData xydata, BorderPoint cursor, int border_width, int did_leftturn){
    int dxi = getdx(cursor.dir+RIGHT);
    int dyi = getdy(cursor.dir+RIGHT);
    int dxj = getdx(cursor.dir+RIGHT+RIGHT);
    int dyj = getdy(cursor.dir+RIGHT+RIGHT);
    for (int i=0; i<border_width; i++) {
        int jmax = did_leftturn ? i+1 : 1;
        for (int j=0; j<jmax; j++) {
            int px = cursor.x + i*dxi + j*dxj;
            int py = cursor.y + i*dyi + j*dyj;
            int idx = py*xydata.width + px;
            if (out_of_bounds(xydata, idx)) continue;
            
            // payload
            xydata.dist[idx] = border_width+1;
            xydata.orig_img[idx] = xydata.img[idx];
        }
    }
}

void render_border(XYData xydata, BorderPoint cursor, BorderPoint bp_A, BorderPoint bp_B, int border_width, int did_leftturn) {
    const float rel_strength = 0.05;
    
    int dxi = getdx(cursor.dir+RIGHT);
    int dyi = getdy(cursor.dir+RIGHT);
    int dxj = getdx(cursor.dir+RIGHT+RIGHT);
    int dyj = getdy(cursor.dir+RIGHT+RIGHT);
    for (int i=0; i<border_width; i++) {
        int jmax = did_leftturn ? i+1 : 1;
        for (int j=0; j<jmax; j++) {
            int px = cursor.x + i*dxi + j*dxj;
            int py = cursor.y + i*dyi + j*dyj;
            int idx = py*xydata.width + px;
            if (out_of_bounds(xydata, idx)) continue;
            
            // payload
            float alpha = 1.0; //FIXME
            float dist = i+j+alpha - 0.5;
            if (dist <= 1e-10) dist = 1e-10;
            
            if (xydata.dist[idx] > dist) {
                xydata.dist[idx] = dist;
                // normal is perpendicular to tangent!
                // also y axis in our float world points upward
                float deltax = bp_B.y - bp_A.y;
                float deltay = bp_B.x - bp_A.x;
                float norm = sqrt(deltax*deltax + deltay*deltay);
                deltax /= norm;
                deltay /= norm;
                
                // correction for "lattice spacing"
                dist *=fmax(fabs(deltax), fabs(deltay));
                
                // illumination vector (0, 1)
                float cosphi = (deltax*0.0) + (deltay*1.0);
                
                float amount = (border_width/dist);
                amount = 256*rel_strength*amount*amount * cosphi;
                xydata.img[idx] = adjust_pixel(xydata.orig_img[idx], amount);
            }
        }
    }
}

EXPORT void fill(LONG value, LONG array[], uint64_t array_size) {
    for (uint64_t i=0; i<array_size; i++) {
        array[i] = value;
    }
}

EXPORT void outline(LONG img[], int width, int height) {
    int did_leftturn;
    
    XYData xydata;
    BorderPoint backlog[SMOOTH_SIZE];
    BYTE backlog_pos;
    // tracks if the backlog was fully filled when entering stage 2.
    int backlog_full = FALSE;
    // stage 1: init xydata, 2: render border
    int stage = 1;
    
    int border_width = width>height ? width/20 : height/20;
    if (border_width<1) border_width=1;
    
    if (width<1 || height<1) return;
    
    xydata.img = img;
    xydata.width = width;
    xydata.height = height;
    
    BorderPoint cursor = find_start(xydata);
    if (cursor.x < 0) {
        printf("no start point found, aborting.\n");
        return;
    }
    
    xydata.dist = (float*) malloc(width*height*sizeof(float));
    xydata.orig_img = (LONG*) malloc(width*height*sizeof(LONG));
    
    BorderPoint startpoint = cursor;
    backlog[0] = startpoint;
    backlog_pos = 0;
    
    // safety net: exit after 200k steps
    int cnt=0;
    const int maxcnt = 200000;
    for (cnt=0; cnt<maxcnt; cnt++) {
        
        backlog_pos = (backlog_pos+1) % SMOOTH_SIZE;
        if (backlog_pos==0) backlog_full = TRUE;
        cursor = move_to_next(xydata, cursor);
        backlog[backlog_pos] = cursor;
        if (cursor.x < 0) break;
        
        did_leftturn = ((cursor.dir+RIGHT)%3 == backlog[(backlog_pos+SMOOTH_SIZE-1) % SMOOTH_SIZE].dir);
        
        if (stage==1) {
            // stage 1: init arrays where necessary
            init_dist_and_origimg(xydata, cursor, border_width, did_leftturn);
            if (cursor.x == startpoint.x && cursor.y == startpoint.y) {
                stage=2;
                printf("enter stage 2 at cnt=%d", cnt);
            }
        }
        else {
            // This is the emergency exit
            if (!backlog_full) break;
            
            // stage 2: render border
            // point A: SMOOTH_SIZE/2 steps before bp_Center
            // point Center: the point to render
            // point B: SMOOTH_SIZE/2 steps after bp_Center
            BorderPoint bp_A = backlog[(backlog_pos+1) % SMOOTH_SIZE];
            BorderPoint bp_Center = backlog[(backlog_pos+SMOOTH_SIZE/2) % SMOOTH_SIZE];
            BorderPoint bp_B = backlog[backlog_pos];
            render_border(xydata, bp_Center, bp_A, bp_B, border_width, did_leftturn);
            
            if (cursor.x == startpoint.x && cursor.y == startpoint.y) break;
        }
    }
    if (cnt==maxcnt) printf("Aborted after %d steps", maxcnt);
    
    free(xydata.dist);
    free(xydata.orig_img);
}

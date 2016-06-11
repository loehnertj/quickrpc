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

typedef struct {
    int border_width;
    int max_strength;
    float rel_strength;
    float illum_x;
    float illum_y;
} RenderSettings;

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
    dir = (dir & 3);
    // in:  0  1  2  3
    // out: 1  0 -1  0
    return (dir%2) ? 0 : (1-dir);
}

inline int getdy(int dir) {
    dir = (dir & 3);
    // in:  0  1  2  3
    // out: 0  1  0 -1 
    return (dir%2) ? (2-dir) : 0;
}

// rotates the given number of 90deg-steps CW.
void rotate(int* x, int*y, int steps) {
    int x2 = (*x)*getdx(steps) + (*y)*getdx(steps+1);
    int y2 = (*x)*getdy(steps) + (*y)*getdy(steps+1);
    *x = x2;
    *y = y2;
}

// rotates the given number of 90deg-steps CW.
void rotatef(float* x, float*y, int steps) {
    float x2 = (*x)*getdx(steps) + (*y)*getdx(steps+1);
    float y2 = (*x)*getdy(steps) + (*y)*getdy(steps+1);
    *x = x2;
    *y = y2;
}

int get_idx(XYData xydata, int x, int y) {
    if (x<0 || x>=xydata.width) return -1;
    if (y<0 || y>=xydata.height) return -1;
    return y*xydata.width + x;
}

LONG img_safe(XYData xydata, int x, int y) {
    int idx = get_idx(xydata, x, y);
    if (idx<0) return 0;
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
    
    
    int idx = get_idx(xydata, p1x, p1y);
    if (idx>=0) {
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
        idx = get_idx(xydata, p2x, p2y);
        //printf("-> p2=%i %i ", p2x, p2y);
        if (idx>=0) {
            if ((img_safe(xydata, p2x, p2y) & 0xff000000) != 0) {
                // p2 is the next point
                cursor.x = p2x;
                cursor.y = p2y;
                // do not turn
                found_next = TRUE;
                //printf("->go\n");
            }
        }
    }
    if (!found_next) {
        // p1 and p2 transparent => turn RIGHT and try again
        cursor.dir = (cursor.dir + RIGHT) % 4;
        //printf("-> RIGHT\n");
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
        int jmax = did_leftturn ? border_width : 1;
        for (int j=0; j<jmax; j++) {
            int px = cursor.x + i*dxi + j*dxj;
            int py = cursor.y + i*dyi + j*dyj;
            int idx = get_idx(xydata, px, py);
            if (idx<0) continue;
            
            // payload
            xydata.dist[idx] = border_width*2;
            xydata.orig_img[idx] = xydata.img[idx];
        }
    }
}

void render_border(XYData xydata, BorderPoint* backlog, int backlog_pos, int backlog_size, RenderSettings rs) {
    // calculate backlog indices.
    // point A: oldest backlog point
    // point B: 2nd-oldest backlog point
    // point cursor: the point to render
    // point Y: second-newest backlog point
    // point Z: newest backlog point
    int bp_A = (backlog_pos+1) % backlog_size;
    int bp_B = (backlog_pos+2) % backlog_size;
    int bp_Cursor = (backlog_pos + backlog_size/2) % backlog_size;
    int bp_Y = (backlog_pos + backlog_size-1) % backlog_size;
    int bp_Z = backlog_pos;
    
    BorderPoint cursor = backlog[bp_Cursor];
    // Find directions of outline normal on begin and end of cursor segment.
    // outline normal is the smoothed direction vector rotated clockwise 90deg.
    float nx_b = -(backlog[bp_Y].y - backlog[bp_A].y);
    float ny_b = +(backlog[bp_Y].x - backlog[bp_A].x);
    float nx_e = -(backlog[bp_Z].y - backlog[bp_B].y);
    float ny_e = +(backlog[bp_Z].x - backlog[bp_B].x);
    
    // illumination vector -30deg
    float cosphi = -(nx_b+nx_e)*rs.illum_x - (ny_b+ny_e)*rs.illum_y;
    cosphi /= sqrt((nx_b+nx_e)*(nx_b+nx_e) + (ny_b+ny_e)*(ny_b+ny_e));
    
    
    float alpha;
    int idx = get_idx(xydata, cursor.x, cursor.y);
    if (idx<0) {
        alpha=0;
    }
    else {
        alpha = (xydata.orig_img[idx] & 0xff000000) >> 24;
        alpha /= 255.0;
    }
    
    // rotate directions as if cursor segment would point right (direction 0).
    rotatef(&nx_b, &ny_b, -cursor.dir);
    rotatef(&nx_e, &ny_e, -cursor.dir);
    
    // normal points in "outside" direction? Flee in terror.
    if (ny_b<=0 || ny_e<=0) return;
    
    float slope_b = nx_b / ny_b;
    float slope_e = nx_e / ny_e;
    
    // i will count in "inside" direction, j in cursor direction.
    int dxi = getdx(cursor.dir+RIGHT);
    int dyi = getdy(cursor.dir+RIGHT);
    int dxj = getdx(cursor.dir);
    int dyj = getdy(cursor.dir);
    for (int i=0; i<rs.border_width; i++) {
        int j = -sqrt(rs.border_width*rs.border_width - i*i);
        if (j < (slope_b*(i+0.5)-0.5)) {
            j = ceil(slope_b*(i+0.5)-0.5);
        }
        while (j <= (slope_e*(i+0.5))+0.5) {
            if (j*j+i*i>rs.border_width*rs.border_width) break;
            
            int px = cursor.x + i*dxi + j*dxj;
            int py = cursor.y + i*dyi + j*dyj;
            idx = get_idx(xydata, px, py);
            if (idx<0) {
                j++;
                continue;
            }
            
            float dist = sqrt(i*i + j*j) + alpha - 0.5;
            if (dist <= 1e-5) dist = 1e-5;
            
            if (xydata.dist[idx] > dist) {
                xydata.dist[idx] = dist;
                
                float amount = (rs.border_width/dist);
                amount = fmin(256*rs.rel_strength*amount*amount, rs.max_strength) * cosphi;
                xydata.img[idx] = adjust_pixel(xydata.orig_img[idx], amount);
            }
            j++;
        }
    }
}

EXPORT void fill(LONG value, LONG array[], uint64_t array_size) {
    for (uint64_t i=0; i<array_size; i++) {
        array[i] = value;
    }
}

EXPORT void outline(LONG img[], int width, int height, RenderSettings render_settings) {
    /*printf("start outline, settings: bw %d ms %d rs %f ix %f iy %f\n",
           render_settings.border_width,
           render_settings.max_strength,
           render_settings.rel_strength,
           render_settings.illum_x,
           render_settings.illum_y
    );
    */
           
    int did_leftturn;
    
    XYData xydata;
    BorderPoint *backlog;
    BYTE backlog_pos;
    // tracks if the backlog was fully filled when entering stage 2.
    int backlog_full = FALSE;
    // stage 1: init xydata, 2: render border
    int stage = 1;
    
    if (render_settings.border_width<1) render_settings.border_width=1;
    int backlog_size = render_settings.border_width*2;
    
    if (width<1 || height<1) return;
    
    xydata.img = img;
    xydata.width = width;
    xydata.height = height;
    
    BorderPoint cursor = find_start(xydata);
    if (cursor.x < 0) {
        printf("no start point found, aborting.\n");
        return;
    }
    
    backlog = (BorderPoint*) malloc(backlog_size*sizeof(BorderPoint));
    xydata.dist = (float*) malloc(width*height*sizeof(float));
    xydata.orig_img = (LONG*) malloc(width*height*sizeof(LONG));
    
    BorderPoint startpoint = cursor;
    backlog[0] = startpoint;
    backlog_pos = 0;
    
    // safety net: exit after 200k steps
    int cnt=0;
    const int maxcnt = 200000;
    for (cnt=0; cnt<maxcnt; cnt++) {
        
        backlog_pos = (backlog_pos+1) % backlog_size;
        if (backlog_pos==0) backlog_full = TRUE;
        cursor = move_to_next(xydata, cursor);
        //printf("%d %d %d\n", cursor.x, cursor.y, cursor.dir);
        backlog[backlog_pos] = cursor;
        if (cursor.x < 0) break;
        
        
        if (stage==1) {
            // stage 1: init arrays where necessary
            did_leftturn = (((cursor.dir+RIGHT)& 3) == backlog[(backlog_pos+backlog_size-1) % backlog_size].dir);
            init_dist_and_origimg(xydata, cursor, render_settings.border_width, did_leftturn);
            if (cursor.x == startpoint.x && cursor.y == startpoint.y && cursor.dir == startpoint.dir) {
                stage=2;
                //printf("enter stage 2 at cnt=%d", cnt);
            }
        }
        else {
            // This is the emergency exit
            if (!backlog_full) break;
            
            // stage 2: render border
            render_border(xydata, backlog, backlog_pos, backlog_size, render_settings);
            
            if (cursor.x == startpoint.x && cursor.y == startpoint.y) break;
        }
    }
    if (cnt==maxcnt) printf("Aborted after %d steps", maxcnt);
    
    free(xydata.dist);
    free(xydata.orig_img);
    free(backlog);
}

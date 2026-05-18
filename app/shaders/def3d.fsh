#version 430 core

in vec3 v_color;
in vec2 v_texcoord;
in vec3 v_rgb;
in float v_alpha;
in vec2 v_view_size;
in float v_inv_depth;

out vec4 FragColor;

uniform sampler2D u_texture;

void main()
{
    vec4 texColor = texture(u_texture, v_texcoord);
    FragColor = texColor * vec4(v_color * v_rgb, v_alpha);
}